import logging
import uuid
from datetime import datetime
from functools import lru_cache
from functools import wraps
from time import sleep

from cachetools import TTLCache
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, ConfigDict
from vertexai.generative_models import ChatSession

from .config import Settings, TmdbImagesConfig, load_tmdb_images_config, QuizConfig
from .gemini import GeminiClient, GeminiQuestion, GeminiAnswer
from .prompt import PromptGenerator, get_personality_by_name, get_language_by_name
from .tmdb import TmdbClient

logger: logging.Logger = logging.getLogger(__name__)


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    quiz_id: str
    chat: ChatSession
    question: GeminiQuestion
    movie: dict
    started_at: datetime


class UserAnswer(BaseModel):
    answer: str


class StartQuizResponse(BaseModel):
    quiz_id: str
    question: GeminiQuestion
    movie: dict


class FinishQuizResponse(BaseModel):
    quiz_id: str
    question: GeminiQuestion
    movie: dict
    user_answer: str
    result: GeminiAnswer


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

app: FastAPI = FastAPI()

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
        1: 100
    }.get(popularity, 1)


def _get_page_max(popularity: int) -> int:
    return {
        3: 5,
        2: 100,
        1: 300
    }.get(popularity, 3)


call_count: int = 0
last_reset_time: datetime = datetime.now()


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
def get_movies(page: int = 1, vote_avg_min: float = 5.0, vote_count_min: float = 1000.0):
    return tmdb_client.get_movies(page, vote_avg_min, vote_count_min)


@app.get('/movies/random')
def get_random_movie(page_min: int = 1, page_max: int = 3, vote_avg_min: float = 5.0, vote_count_min: float = 1000.0):
    return tmdb_client.get_random_movie(page_min, page_max, vote_avg_min, vote_count_min)


@app.get('/sessions')
def get_sessions():
    return [SessionResponse(
        quiz_id=session.quiz_id,
        question=session.question,
        movie=session.movie,
        started_at=session.started_at
    ) for session in session_cache.values()]


@app.get('/limit')
def get_limit():
    return LimitResponse(
        daily_limit=settings.quiz_rate_limit,
        quiz_count=call_count,
        last_reset_time=last_reset_time,
        last_reset_date=last_reset_time.date(),
        current_date=datetime.now().date()
    )


@app.post('/quiz')
@rate_limit
@retry(max_retries=settings.quiz_max_retries)
def start_quiz(quiz_config: QuizConfig = QuizConfig()):
    movie = tmdb_client.get_random_movie(
        page_min=_get_page_min(quiz_config.popularity),
        page_max=_get_page_max(quiz_config.popularity),
        vote_avg_min=quiz_config.vote_avg_min,
        vote_count_min=quiz_config.vote_count_min
    )

    genres = [genre['name'] for genre in movie['genres']]

    prompt = prompt_generator.generate_question_prompt(
        movie_title=movie['title'],
        language=get_language_by_name(quiz_config.language),
        personality=get_personality_by_name(quiz_config.personality),
        tagline=movie['tagline'],
        overview=movie['overview'],
        genres=', '.join(genres),
        budget=movie['budget'],
        revenue=movie['revenue'],
        average_rating=movie['vote_average'],
        rating_count=movie['vote_count'],
        release_date=movie['release_date'],
        runtime=movie['runtime']
    )

    chat = gemini_client.start_chat()

    logger.debug('starting quiz with generated prompt: %s', prompt)
    gemini_reply = gemini_client.get_chat_response(chat, prompt)
    gemini_question = gemini_client.parse_gemini_question(gemini_reply)

    quiz_id = str(uuid.uuid4())
    session_cache[quiz_id] = SessionData(
        quiz_id=quiz_id,
        chat=chat,
        question=gemini_question,
        movie=movie,
        started_at=datetime.now()
    )

    return StartQuizResponse(quiz_id=quiz_id, question=gemini_question, movie=movie)


@app.post('/quiz/{quiz_id}/answer')
@retry(max_retries=settings.quiz_max_retries)
def finish_quiz(quiz_id: str, user_answer: UserAnswer):
    session_data = session_cache.get(quiz_id)

    if not session_data:
        logger.info('session not found: %s', quiz_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')

    prompt = prompt_generator.generate_answer_prompt(answer=user_answer.answer)

    chat = session_data.chat
    del session_cache[quiz_id]

    logger.debug('evaluating quiz answer with generated prompt: %s', prompt)
    gemini_reply = gemini_client.get_chat_response(chat, prompt)
    gemini_answer = gemini_client.parse_gemini_answer(gemini_reply)

    return FinishQuizResponse(
        quiz_id=quiz_id,
        question=session_data.question,
        movie=session_data.movie,
        user_answer=user_answer.answer,
        result=gemini_answer
    )
