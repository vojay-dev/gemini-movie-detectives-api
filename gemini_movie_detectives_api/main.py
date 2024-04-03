import random
import uuid
from functools import lru_cache
from typing import List

import httpx
import vertexai
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException
from google.oauth2 import service_account
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel, ConfigDict
from starlette import status
from vertexai.generative_models import GenerativeModel, ChatSession

from .config import Settings, TmdbImagesConfiguration, load_tmdb_images_configuration


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    chat: ChatSession
    question: dict
    movie: dict


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_tmdb_images_configuration() -> TmdbImagesConfiguration:
    return load_tmdb_images_configuration(get_settings())


settings: Settings = get_settings()
tmdb_images_configuration: TmdbImagesConfiguration = get_tmdb_images_configuration()

app: FastAPI = FastAPI()

credentials = service_account.Credentials.from_service_account_file('gcp-vojay-gemini.json')
vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location, credentials=credentials)
model = GenerativeModel('gemini-1.0-pro')

env = Environment(
    loader=PackageLoader('gemini_movie_detectives_api'),
    autoescape=select_autoescape()
)

# Cache for quiz session
session_cache = TTLCache(maxsize=100, ttl=3600)


def get_poster_url(poster_path: str, size='original') -> str:
    base_url = tmdb_images_configuration.secure_base_url

    if size not in tmdb_images_configuration.poster_sizes:
        size = 'original'

    return f'{base_url}{size}{poster_path}'


def get_movies(page: int, vote_avg_min: float, vote_count_min: float) -> List[dict]:
    response = httpx.get('https://api.themoviedb.org/3/discover/movie', headers={
        'Authorization': f'Bearer {settings.tmdb_api_key}'
    }, params={
        'sort_by': 'popularity.desc',
        'include_adult': 'false',
        'include_video': 'false',
        'language': 'en-US',
        'with_original_language': 'en',
        'vote_average.gte': vote_avg_min,
        'vote_count.gte': vote_count_min,
        'page': page
    })

    movies = response.json()['results']

    for movie in movies:
        movie['poster_url'] = get_poster_url(movie['poster_path'])

    return movies


def get_random_movie(
    page_min: int = settings.tmdb_page_min,
    page_max: int = settings.tmdb_page_max,
    vote_avg_min: float = settings.tmdb_vote_avg_min,
    vote_count_min: float = settings.tmdb_vote_count_min
):
    movies = get_movies(random.randint(page_min, page_max), vote_avg_min, vote_count_min)
    return get_movie_details(random.choice(movies)['id'])


@lru_cache(maxsize=1024)
def get_movie_details(movie_id: int):
    response = httpx.get(f'https://api.themoviedb.org/3/movie/{movie_id}', headers={
        'Authorization': f'Bearer {settings.tmdb_api_key}'
    }, params={
        'language': 'en-US'
    })

    movie = response.json()
    movie['poster_url'] = get_poster_url(movie['poster_path'])

    return movie


def get_chat_response(chat: ChatSession, prompt: str) -> str:
    text_response = []
    responses = chat.send_message(prompt, stream=True)
    for chunk in responses:
        text_response.append(chunk.text)
    return "".join(text_response)


def parse_gemini_question(gemini_reply: str):
    question = None
    hint1 = None
    hint2 = None

    for line in gemini_reply.splitlines():
        if line.startswith('Question:'):
            question = line[9:].lstrip().rstrip()
        elif line.startswith('Hint 1:'):
            hint1 = line[7:].lstrip().rstrip()
        elif line.startswith('Hint 2:'):
            hint2 = line[7:].lstrip().rstrip()

    if not question or not hint1 or not hint2:
        raise ValueError(f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}')

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


@app.get('/movies')
def get_movies(page: int = 1, vote_avg_min: float = 5.0, vote_count_min: float = 1000.0):
    return get_movies(page, vote_avg_min, vote_count_min)


@app.get('/movies/random')
def get_random_movie():
    return get_random_movie()


@app.post('/quiz')
def start_quiz():
    template = env.get_template('prompt_question.jinja')
    movie = get_random_movie()

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
    question = parse_gemini_question(gemini_reply)

    quiz_id = str(uuid.uuid4())
    session_cache[quiz_id] = SessionData(chat=chat, question=question, movie=movie)

    return {
        'quiz_id': quiz_id,
        'question': question,
        'movie': movie
    }


@app.post('/quiz/{quiz_id}/answer')
def answer_quiz(quiz_id: str, answer: str):
    session_data = session_cache.get(quiz_id)

    if not session_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    template = env.get_template('prompt_answer.jinja')
    prompt = template.render(answer=answer)

    chat = session_data.chat
    del session_cache[quiz_id]

    gemini_reply = get_chat_response(chat, prompt)
    answer = parse_gemini_answer(gemini_reply)

    return {
        'quiz_id': quiz_id,
        'question': session_data.question,
        'movie': session_data.movie,
        'answer': answer
    }
