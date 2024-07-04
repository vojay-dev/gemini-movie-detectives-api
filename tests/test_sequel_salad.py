import unittest
from unittest.mock import Mock

from gemini_movie_detectives_api.model import Personality, SequelSaladData
from gemini_movie_detectives_api.quiz.sequel_salad import SequelSalad
from gemini_movie_detectives_api.template import TemplateManager


class TestSequelSalad(unittest.TestCase):

    def test_start_quiz(self):
        template_manager = TemplateManager()

        gemini_client = Mock()
        imagen_client = Mock()
        speech_client = Mock()
        firestore_client = Mock()
        tmdb_client = Mock()
        wiki_client = Mock()
        chat_session = Mock()

        franchises = ['franchise1', 'franchise2']
        firestore_client.get_franchises.return_value = franchises

        gemini_client.get_chat_response.return_value = '{"sequel_plot": "plot", "sequel_title": "title", "poster_prompt": "prompt"}'

        speech_client.synthesize_to_file.return_value = 'audio.mp3'
        imagen_client.generate_image.return_value = 'poster.jpg'

        sequel_salad = SequelSalad(template_manager, gemini_client, imagen_client, speech_client, firestore_client, tmdb_client, wiki_client)
        sequel_salad_data: SequelSaladData = sequel_salad.start_quiz(Personality.DEFAULT, chat_session)

        self.assertIn(sequel_salad_data.franchise, franchises)
        self.assertEqual('audio.mp3', sequel_salad_data.speech)
        self.assertEqual('poster.jpg', sequel_salad_data.poster)

        self.assertEqual('plot', sequel_salad_data.question.sequel_plot)
        self.assertEqual('title', sequel_salad_data.question.sequel_title)
        self.assertEqual('prompt', sequel_salad_data.question.poster_prompt)


if __name__ == '__main__':
    unittest.main()
