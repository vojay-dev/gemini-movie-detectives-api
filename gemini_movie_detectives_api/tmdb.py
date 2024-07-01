import random
from functools import lru_cache
from typing import List

import httpx

from gemini_movie_detectives_api.config import TmdbImagesConfig


class TmdbClient:

    def __init__(self, tmdb_api_key: str, tmdb_images_config: TmdbImagesConfig):
        self.tmdb_images_config = tmdb_images_config
        self.tmdb_api_key = tmdb_api_key

    def get_poster_url(self, poster_path: str, size='original') -> str:
        base_url = self.tmdb_images_config.secure_base_url

        if size not in self.tmdb_images_config.poster_sizes:
            size = 'original'

        return f'{base_url}{size}{poster_path}'

    def get_movies(self, page: int, vote_avg_min: float, vote_count_min: float) -> List[dict]:
        response = httpx.get('https://api.themoviedb.org/3/discover/movie', headers={
            'Authorization': f'Bearer {self.tmdb_api_key}'
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
            movie['poster_url'] = self.get_poster_url(movie['poster_path'])

        return movies

    def get_random_movie(self, page_min: int, page_max: int, vote_avg_min: float, vote_count_min: float) -> dict | None:
        movies = self.get_movies(random.randint(page_min, page_max), vote_avg_min, vote_count_min)
        if not movies:
            return None

        return self.get_movie_details(random.choice(movies)['id'])

    @lru_cache(maxsize=1024)
    def get_movie_details(self, movie_id: int) -> dict:
        response = httpx.get(f'https://api.themoviedb.org/3/movie/{movie_id}', headers={
            'Authorization': f'Bearer {self.tmdb_api_key}'
        }, params={
            'language': 'en-US'
        })

        movie = response.json()
        movie['poster_url'] = self.get_poster_url(movie['poster_path'])

        return movie
