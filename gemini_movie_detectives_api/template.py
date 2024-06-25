from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from gemini_movie_detectives_api.model import Personality, QuizType


class TemplateManager:

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader('gemini_movie_detectives_api'),
            autoescape=select_autoescape()
        )

    def render_template(self, quiz_type: QuizType, name: str, **kwargs: Any) -> str:
        return self.env.get_template(f'{quiz_type.value}/{name}.jinja').render(**kwargs)

    def render_personality(self, personality: Personality) -> str:
        return self.env.get_template(f'personality/{personality.value}.jinja').render()
