import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    gcp_gemini_model: str = 'gemini-1.5-pro-001'
    gcp_imagen_model: str = 'imagegeneration@006'
    gcp_tts_lang: str = 'en-US'
    gcp_tts_voice: str = 'en-US-Studio-M'
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
