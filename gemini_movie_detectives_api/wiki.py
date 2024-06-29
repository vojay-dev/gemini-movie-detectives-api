import random
from time import sleep

import wikipedia
from pydantic import BaseModel

from gemini_movie_detectives_api.tmdb import TmdbClient


class MovieFacts(BaseModel):
    movie_title: str
    facts: str
    movie: dict


class WikiClient:

    MAX_RETRIES = 5
    RETRY_DELAY = 1

    def __init__(self, tmdb_client: TmdbClient):
        self.tmdb_client = tmdb_client
        wikipedia.set_lang('en')

    def get_random_movie_facts(self) -> MovieFacts:
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                # The following config ensures to get rather familiar movies
                random_movie = self.tmdb_client.get_random_movie(
                    page_min=1,
                    page_max=10,
                    vote_avg_min=4.0,
                    vote_count_min=4000
                )

                original_title = random_movie['original_title']
                related_pages = wikipedia.search(original_title)
                if not related_pages:
                    raise ValueError(f'No Wikipedia page found for {original_title}')

                return MovieFacts(
                    movie_title=original_title,
                    facts=wikipedia.page(related_pages[0]).content,
                    movie=random_movie
                )
            except BaseException as e:
                retries += 1
                if retries >= self.MAX_RETRIES:
                    raise ValueError("Failed to get random movie facts after multiple attempts") from e
                sleep(self.RETRY_DELAY)

    @staticmethod
    def get_random_bttf_facts() -> str:
        related_pages = wikipedia.search('Back to the Future')
        if not related_pages:
            raise ValueError(f'No Wikipedia page found')

        return wikipedia.page(random.choice(related_pages)).content
