import unittest

from jinja2 import Environment, PackageLoader, select_autoescape

from gemini_movie_detectives_api.prompt import PromptGenerator, Language, Personality


class TestPrompt(unittest.TestCase):

    def test_generate_question_prompt(self):
        env = Environment(
            loader=PackageLoader('gemini_movie_detectives_api'),
            autoescape=select_autoescape()
        )

        movie_title = 'movie_title'
        tagline = 'tagline'
        overview = 'overview'
        genres = 'action, comedy'

        prompt_generator = PromptGenerator()
        prompt = prompt_generator.generate_question_prompt(
            movie_title,
            Language.DEFAULT,
            Personality.DEFAULT,
            tagline=tagline,
            overview=overview,
            genres=genres
        )

        language = env.get_template(f'language/{Language.DEFAULT.value}').render()
        self.assertIn(language, prompt)

        metadata = env.get_template('metadata.jinja').render(
            tagline=tagline,
            overview=overview,
            genres=genres
        )
        self.assertIn(metadata, prompt)

    def test_generate_answer_prompt(self):
        env = Environment(
            loader=PackageLoader('gemini_movie_detectives_api'),
            autoescape=select_autoescape()
        )

        answer = 'some movie'

        prompt_generator = PromptGenerator()
        prompt = prompt_generator.generate_answer_prompt(answer)

        expected = env.get_template('prompt_answer.jinja').render(answer=answer)
        self.assertEqual(expected, prompt)


if __name__ == '__main__':
    unittest.main()
