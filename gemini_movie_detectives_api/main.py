import re
import uuid
from datetime import datetime
from functools import lru_cache
from functools import wraps
from time import sleep

import vertexai
from cachetools import TTLCache
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel, ConfigDict
from vertexai.generative_models import GenerativeModel, ChatSession

from .config import Settings, TmdbImagesConfig, load_tmdb_images_config, GENERATION_CONFIG, QuizConfig
from .tmdb import TmdbClient


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    quiz_id: str
    chat: ChatSession
    question: dict
    movie: dict
    started_at: datetime


class UserAnswer(BaseModel):
    answer: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_tmdb_images_config() -> TmdbImagesConfig:
    return load_tmdb_images_config(get_settings())


settings: Settings = get_settings()
tmdb_client: TmdbClient = TmdbClient(settings.tmdb_api_key, get_tmdb_images_config())

app: FastAPI = FastAPI()

# for local development
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
]

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

credentials = service_account.Credentials.from_service_account_file(settings.gcp_service_account_file)
vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location, credentials=credentials)
model = GenerativeModel('gemini-1.0-pro')

env = Environment(
    loader=PackageLoader('gemini_movie_detectives_api'),
    autoescape=select_autoescape()
)

# cache for quiz session, ttl = max session duration in seconds
session_cache = TTLCache(maxsize=100, ttl=600)


def get_chat_response(chat: ChatSession, prompt: str) -> str:
    text_response = []
    responses = chat.send_message(prompt, generation_config=GENERATION_CONFIG, stream=True)
    for chunk in responses:
        text_response.append(chunk.text)
    return "".join(text_response)


def parse_gemini_question(gemini_reply: str):
    result = re.findall(r'[^:]+: ([^\n]+)', gemini_reply, re.MULTILINE)
    if len(result) != 3:
        raise ValueError(f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}')

    question = result[0]
    hint1 = result[1]
    hint2 = result[2]

    return {
        'question': question,
        'hint1': hint1,
        'hint2': hint2
    }


def parse_gemini_answer(gemini_reply: str):
    points = None
    answer = None

    for line in gemini_reply.splitlines():
        if line.startswith('Points:'):
            points = line[7:].lstrip().rstrip()
        elif line.startswith('Answer:'):
            answer = line[7:].lstrip().rstrip()

    if not points or not answer:
        raise ValueError(f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}')

    return {
        'points': points,
        'answer': answer
    }


def get_page_min(popularity: int) -> int:
    return {
        3: 1,
        2: 10,
        1: 100
    }.get(popularity, 1)


def get_page_max(popularity: int) -> int:
    return {
        3: 5,
        2: 100,
        1: 300
    }.get(popularity, 3)


def retry(max_retries: int):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ValueError as e:
                    print(f"Error in {func.__name__}: {e}")
                    if _ < max_retries - 1:
                        print('Retrying...')
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
    return [{
        'quiz_id': session.quiz_id,
        'question': session.question,
        'movie': session.movie,
        'started_at': session.started_at
    } for session in session_cache.values()]


@app.post('/quiz')
@retry(max_retries=settings.quiz_max_retries)
def start_quiz(quiz_config: QuizConfig):
    template = env.get_template('prompt_question.jinja')

    movie = tmdb_client.get_random_movie(
        page_min=get_page_min(quiz_config.popularity),
        page_max=get_page_max(quiz_config.popularity),
        vote_avg_min=quiz_config.vote_avg_min,
        vote_count_min=quiz_config.vote_avg_max
    )

    genres = [genre['name'] for genre in movie['genres']]

    prompt = template.render(
        title=movie['title'],
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

    chat = model.start_chat()

    print('prompt:', prompt)
    gemini_reply = get_chat_response(chat, prompt)
    gemini_question = parse_gemini_question(gemini_reply)

    quiz_id = str(uuid.uuid4())
    session_cache[quiz_id] = SessionData(
        quiz_id=quiz_id,
        chat=chat,
        question=gemini_question,
        movie=movie,
        started_at=datetime.now()
    )

    return {
        'quiz_id': quiz_id,
        'question': gemini_question,
        'movie': movie
    }


@app.post('/quiz/{quiz_id}/answer')
@retry(max_retries=settings.quiz_max_retries)
def finish_quiz(quiz_id: str, user_answer: UserAnswer):
    session_data = session_cache.get(quiz_id)

    if not session_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    template = env.get_template('prompt_answer.jinja')
    prompt = template.render(answer=user_answer.answer)

    chat = session_data.chat
    del session_cache[quiz_id]

    gemini_reply = get_chat_response(chat, prompt)
    gemini_answer = parse_gemini_answer(gemini_reply)

    return {
        'quiz_id': quiz_id,
        'question': session_data.question,
        'movie': session_data.movie,
        'user_answer': user_answer.answer,
        'answer': gemini_answer
    }
