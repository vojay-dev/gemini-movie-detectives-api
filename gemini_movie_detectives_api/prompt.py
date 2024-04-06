from enum import StrEnum
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape


class Personality(StrEnum):
    DEFAULT = 'default.jinja'
    CHRISTMAS = 'christmas.jinja'
    SCIENTIST = 'scientist.jinja'
    DAD = 'dad.jinja'


class Language(StrEnum):
    DEFAULT = 'en.jinja'
    GERMAN = 'de.jinja'


def get_personality_by_name(name: str) -> Personality:
    try:
        return Personality[name.upper()]
    except KeyError:
        return Personality.DEFAULT


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

    def generate_question_prompt(
        self,
        movie_title: str,
        language: Language,
        personality: Personality,
        **kwargs: Any
    ) -> str:
        template = self.env.get_template('prompt_question.jinja')

        # noinspection PyTypeChecker
        language = self.env.get_template(f'language/{language.value}').render()

        # noinspection PyTypeChecker
        personality = self.env.get_template(f'personality/{personality.value}').render()

        return template.render(
            language=language,
            personality=personality,
            title=movie_title,
            **kwargs
        )

    def generate_answer_prompt(self, answer: str) -> str:
        template = self.env.get_template('prompt_answer.jinja')
        return template.render(answer=answer)
