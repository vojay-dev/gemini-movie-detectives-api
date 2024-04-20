import httpx
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from gemini_movie_detectives_api.prompt import Personality, Language

GENERATION_CONFIG = {
    'temperature': 0.5
}


class QuizConfig(BaseModel):
    vote_avg_min: float = Field(5.0, ge=0.0, le=9.0)
    vote_count_min: float = Field(1000.0, ge=0.0)
    popularity: int = Field(1, ge=1, le=3)
    personality: str = Personality.DEFAULT.name
    language: str = Language.DEFAULT.name


class TmdbImagesConfig(BaseModel):
    base_url: str
    secure_base_url: str
    backdrop_sizes: list[str]
    logo_sizes: list[str]
    poster_sizes: list[str]
    profile_sizes: list[str]
    still_sizes: list[str]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    tmdb_api_key: str
    stats_path: str = '/tmp/movie-detectives/stats.pkl'
    gcp_gemini_model: str = 'gemini-1.0-pro'
    gcp_project_id: str
    gcp_location: str
    gcp_service_account_file: str
    quiz_rate_limit: int = 200
    quiz_max_retries: int = 10


def load_tmdb_images_config(settings: Settings) -> TmdbImagesConfig:
    response = httpx.get('https://api.themoviedb.org/3/configuration', headers={
        'Authorization': f'Bearer {settings.tmdb_api_key}'
    })

    return TmdbImagesConfig(**response.json()['images'])
