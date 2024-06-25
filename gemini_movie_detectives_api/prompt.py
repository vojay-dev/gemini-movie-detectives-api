from enum import StrEnum
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic.v1 import validate_arguments

from gemini_movie_detectives_api.model import Personality

PERSONALITY_PATH = 'personality'
LANGUAGE_PATH = 'language'


class Language(StrEnum):
    DEFAULT = 'en.jinja'
    GERMAN = 'de.jinja'


def get_language_by_name(name: str) -> Language:
    try:
        return Language[name.upper()]
    except KeyError:
        return Language.DEFAULT


class PromptGenerator:

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader('gemini_movie_detectives_api'),
            autoescape=select_autoescape()
        )

    @validate_arguments
    def generate_question_prompt(
        self,
        movie_title: str,
        language: Language,
        personality: Personality,
        **kwargs: Any
    ) -> str:
        template = self.env.get_template('prompt_question.jinja')

        # noinspection PyTypeChecker
        language = self.env.get_template(f'{LANGUAGE_PATH}/{language.value}').render()

        # noinspection PyTypeChecker
        personality = self.env.get_template(f'{PERSONALITY_PATH}/{personality.value}.jinja').render()

        return template.render(
            language=language,
            personality=personality,
            title=movie_title,
            **kwargs
        )

    def generate_answer_prompt(self, answer: str) -> str:
        template = self.env.get_template('prompt_answer.jinja')
        return template.render(answer=answer)
