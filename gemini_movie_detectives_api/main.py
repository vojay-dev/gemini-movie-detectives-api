import logging
import os
import pickle
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
from functools import wraps
from pathlib import Path
from time import sleep

from cachetools import TTLCache
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from starlette.responses import FileResponse

from .config import Settings, TmdbImagesConfig, load_tmdb_images_config
from .gemini import GeminiClient
from .model import Stats, LimitResponse, SessionResponse, StatsResponse, SessionData, \
    FinishQuizResponse, \
    QuizType, StartQuizResponse, FinishQuizRequest, StartQuizRequest
from .quiz.sequel_salad import SequelSalad
from .quiz.title_detectives import TitleDetectives
from .speech import SpeechClient
from .template import TemplateManager
from .tmdb import TmdbClient

logger: logging.Logger = logging.getLogger(__name__)


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
template_manager: TemplateManager = TemplateManager()

tmp_audio_dir = Path("/tmp/movie-detectives/audio")
tmp_audio_dir.mkdir(parents=True, exist_ok=True)
speech_client: SpeechClient = SpeechClient(tmp_audio_dir, credentials)

title_detectives = TitleDetectives(tmdb_client, template_manager, gemini_client, speech_client)
sequel_salad = SequelSalad(template_manager, gemini_client, speech_client)


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
        quiz_type=session.quiz_type,
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


@app.post('/quiz/{quiz_type}')
@retry(max_retries=settings.quiz_max_retries)
def start_quiz(quiz_type: QuizType, request: StartQuizRequest) -> StartQuizResponse:
    if quiz_type != request.quiz_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid start quiz request')

    quiz_id = str(uuid.uuid4())

    personality = request.personality
    chat = gemini_client.start_chat()

    match quiz_type:
        case QuizType.TITLE_DETECTIVES: quiz_data = title_detectives.start_title_detectives(personality, chat)
        case QuizType.SEQUEL_SALAD: quiz_data = sequel_salad.start_sequel_salad()  # todo
        case QuizType.BTTF_TRIVIA: quiz_data = title_detectives.start_title_detectives(personality, chat)  # todo
        case QuizType.TRIVIA: quiz_data = title_detectives.start_title_detectives(personality, chat)  # todo
        case _: raise HTTPException(status_code=400, detail=f'Quiz type {quiz_type} is not supported')

    session_cache[quiz_id] = SessionData(
        quiz_id=quiz_id,
        quiz_type=quiz_type,
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


@app.post('/quiz/{quiz_id}/answer')
@retry(max_retries=settings.quiz_max_retries)
def finish_quiz(quiz_id: str, request: FinishQuizRequest) -> FinishQuizResponse:
    if not quiz_id == request.quiz_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid finish quiz request')

    session_data: SessionData = session_cache.get(quiz_id)

    if not session_data:
        logger.info('session not found: %s', quiz_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')

    quiz_type = session_data.quiz_type
    quiz_data = session_data.quiz_data
    chat = session_data.chat

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Could not load Gemini chat session')

    answer = request.answer
    del session_cache[quiz_id]

    match quiz_type:
        case QuizType.TITLE_DETECTIVES: result = title_detectives.finish_title_detectives(answer, quiz_data, chat)
        case QuizType.SEQUEL_SALAD: result = sequel_salad.finish_sequel_salad(answer, quiz_data)  # todo
        case QuizType.BTTF_TRIVIA: result = title_detectives.finish_title_detectives(answer, quiz_data, chat)  # todo
        case QuizType.TRIVIA: result = title_detectives.finish_title_detectives(answer, quiz_data, chat)  # todo
        case _: raise HTTPException(status_code=400, detail=f'Quiz type {quiz_type} is not supported')

    return FinishQuizResponse(
        quiz_id=quiz_id,
        quiz_result=result
    )


@app.get('/audio/{file_id}.mp3', response_class=FileResponse)
async def get_audio(file_id: str):
    audio_file_path = Path(f'{speech_client.tmp_audio_dir}/{file_id}.mp3')

    if not audio_file_path.exists():
        raise HTTPException(status_code=404, detail='Audio file not found')

    return FileResponse(audio_file_path)
