import logging
import os
import pickle
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from functools import lru_cache
from functools import wraps
from pathlib import Path
from time import sleep
from typing import Union

from cachetools import TTLCache
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from google.api_core.exceptions import GoogleAPIError
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, ConfigDict
from starlette.responses import FileResponse, JSONResponse
from vertexai.generative_models import ChatSession

from .config import Settings, TmdbImagesConfig, load_tmdb_images_config, QuizConfig
from .gemini import GeminiClient, GeminiQuestion, GeminiAnswer
from .prompt import PromptGenerator, get_personality_by_name, get_language_by_name, Language
from .speech import SpeechClient
from .tmdb import TmdbClient

logger: logging.Logger = logging.getLogger(__name__)


class QuizType(str, Enum):
    TITLE_DETECTIVES = 'title-detectives'
    SEQUEL_SALAD = 'sequel-salad'
    BTTF_TRIVIA = 'bttf-trivia'
    TRIVIA = 'trivia'


class UserAnswer(BaseModel):
    answer: str


class TitleDetectivesData(BaseModel):
    question: GeminiQuestion
    movie: dict
    speech: str


class StartQuizResponse(BaseModel):
    quiz_id: str
    quiz_type: QuizType
    quiz_data: Union[TitleDetectivesData, dict]


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    quiz_id: str
    quiz_data: Union[TitleDetectivesData, dict]
    chat: ChatSession
    started_at: datetime


class FinishQuizResponse(BaseModel):
    quiz_id: str
    question: GeminiQuestion
    movie: dict
    user_answer: str
    result: GeminiAnswer
    speech: str


class SessionResponse(BaseModel):
    quiz_id: str
    question: GeminiQuestion
    movie: dict
    started_at: datetime


class LimitResponse(BaseModel):
    daily_limit: int
    quiz_count: int
    last_reset_time: datetime
    last_reset_date: datetime
    current_date: datetime


class Stats(BaseModel):
    quiz_count_total: int = 0
    points_total: int = 0


class StatsResponse(BaseModel):
    stats: Stats
    limit: LimitResponse


@lru_cache
def _get_settings() -> Settings:
    return Settings()


@lru_cache
def _get_tmdb_images_config() -> TmdbImagesConfig:
    return load_tmdb_images_config(_get_settings())


settings: Settings = _get_settings()

tmdb_client: TmdbClient = TmdbClient(settings.tmdb_api_key, _get_tmdb_images_config())
credentials: Credentials = service_account.Credentials.from_service_account_file(settings.gcp_service_account_file)
gemini_client: GeminiClient = GeminiClient(
    settings.gcp_project_id,
    settings.gcp_location,
    credentials,
    settings.gcp_gemini_model
)
prompt_generator: PromptGenerator = PromptGenerator()

tmp_audio_dir = Path("/tmp/movie-detectives/audio")
tmp_audio_dir.mkdir(parents=True, exist_ok=True)
speech_client: SpeechClient = SpeechClient(tmp_audio_dir, credentials)


stats = Stats()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global stats
    path = Path(settings.stats_path)

    # load stats on startup
    if path.exists():
        with open(settings.stats_path, 'rb') as f:
            stats = pickle.load(f)
    yield

    # persist stats on shutdown
    os.makedirs(path.parent.absolute(), exist_ok=True)
    with path.open('wb') as f:
        pickle.dump(stats, f)


app: FastAPI = FastAPI(lifespan=lifespan)

# for local development
origins = [
    'http://localhost',
    'http://localhost:8080',
    'http://localhost:5173',
]

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# cache for quiz session, ttl = max session duration in seconds
session_cache: TTLCache = TTLCache(maxsize=100, ttl=600)


def _get_page_min(popularity: int) -> int:
    return {
        3: 1,
        2: 10,
        1: 50
    }.get(popularity, 1)


def _get_page_max(popularity: int) -> int:
    return {
        3: 5,
        2: 100,
        1: 300
    }.get(popularity, 3)


call_count: int = 0
last_reset_time: datetime = datetime.now()


def _get_limit_response() -> LimitResponse:
    return LimitResponse(
        daily_limit=settings.quiz_rate_limit,
        quiz_count=call_count,
        last_reset_time=last_reset_time,
        last_reset_date=last_reset_time.date(),
        current_date=datetime.now().date()
    )


def rate_limit(func: callable) -> callable:
    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        global call_count
        global last_reset_time

        # reset call count if the day has changed
        if datetime.now().date() > last_reset_time.date():
            call_count = 0
            last_reset_time = datetime.now()

        if call_count >= settings.quiz_rate_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Daily limit reached')

        call_count += 1
        return func(*args, **kwargs)

    return wrapper


def retry(max_retries: int) -> callable:
    def decorator(func) -> callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ValueError as e:
                    logger.error(f'Error in {func.__name__}: {e}')
                    if _ < max_retries - 1:
                        logger.warning(f'Retrying {func.__name__}...')
                        sleep(1)
                    else:
                        raise e

        return wrapper

    return decorator


@app.get('/movies')
async def get_movies(page: int = 1, vote_avg_min: float = 5.0, vote_count_min: float = 1000.0):
    return tmdb_client.get_movies(page, vote_avg_min, vote_count_min)


@app.get('/movies/random')
async def get_random_movie(page_min: int = 1, page_max: int = 3, vote_avg_min: float = 5.0, vote_count_min: float = 1000.0):
    return tmdb_client.get_random_movie(page_min, page_max, vote_avg_min, vote_count_min)


@app.get('/sessions')
async def get_sessions():
    return [SessionResponse(
        quiz_id=session.quiz_id,
        question=session.question,
        movie=session.movie,
        started_at=session.started_at
    ) for session in session_cache.values()]


@app.get('/limit')
async def get_limit():
    return _get_limit_response()


@app.get('/stats')
async def get_stats():
    return StatsResponse(
        stats=stats,
        limit=_get_limit_response()
    )


@app.post('/quiz/{quiz_id}/answer')
@retry(max_retries=settings.quiz_max_retries)
def finish_quiz(quiz_id: str, user_answer: UserAnswer):
    session_data: SessionData = session_cache.get(quiz_id)

    if not session_data:
        logger.info('session not found: %s', quiz_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')

    try:
        prompt = prompt_generator.generate_answer_prompt(answer=user_answer.answer)

        chat = session_data.chat
        del session_cache[quiz_id]

        logger.debug('evaluating quiz answer with generated prompt: %s', prompt)
        gemini_reply = gemini_client.get_chat_response(chat, prompt)
        gemini_answer = gemini_client.parse_gemini_answer(gemini_reply)

        stats.points_total += gemini_answer.points
        return FinishQuizResponse(
            quiz_id=quiz_id,
            question=session_data.quiz_data.question,
            movie=session_data.quiz_data.movie,
            user_answer=user_answer.answer,
            result=gemini_answer,
            speech=speech_client.synthesize_to_file(gemini_answer.answer)
        )
    except GoogleAPIError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
    except BaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')


@app.get('/audio/{file_id}.mp3', response_class=FileResponse)
async def get_audio(file_id: str):
    audio_file_path = Path(f'{speech_client.tmp_audio_dir}/{file_id}.mp3')

    if not audio_file_path.exists():
        raise HTTPException(status_code=404, detail='Audio file not found')

    return FileResponse(audio_file_path)


@app.post('/quiz/{quiz_type}')
@retry(max_retries=settings.quiz_max_retries)
def start_quiz(quiz_type: QuizType, quiz_config: QuizConfig = QuizConfig()) -> StartQuizResponse:
    quiz_id = str(uuid.uuid4())
    chat = gemini_client.start_chat()

    match quiz_type:
        case QuizType.TITLE_DETECTIVES: quiz_data = start_title_detectives(quiz_config, chat)
        case QuizType.SEQUEL_SALAD: quiz_data = start_sequel_salad()
        case QuizType.BTTF_TRIVIA: quiz_data = start_bttf_trivia()
        case QuizType.TRIVIA: quiz_data = start_trivia()
        case _: raise HTTPException(status_code=400, detail=f'Quiz type {quiz_type} is not supported')

    session_cache[quiz_id] = SessionData(
        quiz_id=quiz_id,
        quiz_data=quiz_data,
        chat=chat,
        started_at=datetime.now()
    )

    stats.quiz_count_total += 1

    return StartQuizResponse(
        quiz_id=quiz_id,
        quiz_type=quiz_type,
        quiz_data=quiz_data
    )


def start_title_detectives(quiz_config: QuizConfig, chat: ChatSession):
    movie = tmdb_client.get_random_movie(
        page_min=1,
        page_max=100,
        vote_avg_min=4.0,
        vote_count_min=800
    )

    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No movie found with given criteria')

    try:
        prompt = prompt_generator.generate_question_prompt(
            movie_title=movie['title'],
            language=Language.DEFAULT,
            personality=get_personality_by_name(quiz_config.personality),
            tagline=movie['tagline'],
            overview=movie['overview'],
            genres=', '.join([genre['name'] for genre in movie['genres']]),
            budget=movie['budget'],
            revenue=movie['revenue'],
            average_rating=movie['vote_average'],
            rating_count=movie['vote_count'],
            release_date=movie['release_date'],
            runtime=movie['runtime']
        )

        logger.debug('starting quiz with generated prompt: %s', prompt)
        gemini_reply = gemini_client.get_chat_response(chat, prompt)
        gemini_question = gemini_client.parse_gemini_question(gemini_reply)

        return TitleDetectivesData(
            question=gemini_question,
            movie=movie,
            speech=speech_client.synthesize_to_file(gemini_question.question),
            chat=chat
        )
    except GoogleAPIError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
    except BaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')


def start_sequel_salad():
    # todo
    return {}


def start_bttf_trivia():
    # todo
    return {}


def start_trivia():
    # todo
    return {}
