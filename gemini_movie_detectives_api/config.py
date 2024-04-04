import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


GENERATION_CONFIG = {
    'temperature': 0.5
}


class TmdbImagesConfiguration(BaseModel):
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
    tmdb_vote_avg_min: float = 5.0
    tmdb_vote_count_min: float = 1000.0
    tmdb_page_min: int = 1
    tmdb_page_max: int = 3
    quiz_max_retries: int = 10
    gcp_project_id: str
    gcp_location: str
    gcp_service_account_file: str


def load_tmdb_images_configuration(settings: Settings) -> TmdbImagesConfiguration:
    response = httpx.get('https://api.themoviedb.org/3/configuration', headers={
        'Authorization': f'Bearer {settings.tmdb_api_key}'
    })

    return TmdbImagesConfiguration(**response.json()['images'])
