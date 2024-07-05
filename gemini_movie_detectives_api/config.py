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
    tmp_images_dir: str = '/tmp/movie-detectives/images'
    tmp_audio_dir: str = '/tmp/movie-detectives/audio'
    cleanup_interval_min: int = 10
    cleanup_file_max_age_sec: int = 3600
    gcp_gemini_model: str = 'gemini-1.5-pro-001'
    gcp_imagen_model: str = 'imagegeneration@006'
    gcp_tts_lang: str = 'en-US'
    gcp_tts_voice: str = 'en-US-Studio-Q'
    gcp_project_id: str
    gcp_location: str
    gcp_service_account_file: str
    firebase_service_account_file: str
    quiz_max_retries: int = 4
    limits_reset_password: str = 'secret'


def load_tmdb_images_config(settings: Settings) -> TmdbImagesConfig:
    response = httpx.get('https://api.themoviedb.org/3/configuration', headers={
        'Authorization': f'Bearer {settings.tmdb_api_key}'
    })

    return TmdbImagesConfig(**response.json()['images'])
