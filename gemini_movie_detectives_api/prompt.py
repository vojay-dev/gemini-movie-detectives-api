from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic.v1 import validate_arguments

from gemini_movie_detectives_api.model import Personality


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
        personality: Personality,
        **kwargs: Any
    ) -> str:
        template = self.env.get_template('prompt_question.jinja')

        # noinspection PyTypeChecker
        personality = self.env.get_template(f'personality/{personality.value}.jinja').render()

        return template.render(
            personality=personality,
            title=movie_title,
            **kwargs
        )

    def generate_answer_prompt(self, answer: str) -> str:
        template = self.env.get_template('prompt_answer.jinja')
        return template.render(answer=answer)
