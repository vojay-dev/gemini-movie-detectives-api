import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


GENERATION_CONFIG = {
    'temperature': 0.5
}


class QuizConfig(BaseModel):
    vote_avg_min: float
    vote_count_min: float
    popularity: int


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
    gcp_project_id: str
    gcp_location: str
    gcp_service_account_file: str
    quiz_max_retries: int = 10


def load_tmdb_images_config(settings: Settings) -> TmdbImagesConfig:
    response = httpx.get('https://api.themoviedb.org/3/configuration', headers={
        'Authorization': f'Bearer {settings.tmdb_api_key}'
    })

    return TmdbImagesConfig(**response.json()['images'])