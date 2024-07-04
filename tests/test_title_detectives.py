import unittest
from unittest.mock import Mock

from gemini_movie_detectives_api.model import Personality, TitleDetectivesData
from gemini_movie_detectives_api.quiz.title_detectives import TitleDetectives
from gemini_movie_detectives_api.template import TemplateManager


class TestTitleDetectives(unittest.TestCase):

    def test_start_quiz(self):
        template_manager = TemplateManager()

        gemini_client = Mock()
        imagen_client = Mock()
        speech_client = Mock()
        firestore_client = Mock()
        tmdb_client = Mock()
        wiki_client = Mock()
        chat_session = Mock()

        tmdb_client.get_random_movie.return_value = {
            'title': 'Some Movie',
            'tagline': 'A Great Adventure',
            'overview': 'Lorem ipsum dolor sit amet',
            'genres': [{'name': 'Action'}, {'name': 'Adventure'}],
            'budget': 1000000,
            'revenue': 2000000,
            'vote_average': 8.0,
            'vote_count': 1000,
            'release_date': '2021-01-01',
            'runtime': 120
        }

        gemini_client.get_chat_response.return_value = '{"question": "What is the movie?", "hint1": "hint1", "hint2": "hint2"}'
        speech_client.synthesize_to_file.return_value = 'audio.mp3'

        title_detectives = TitleDetectives(template_manager, gemini_client, imagen_client, speech_client, firestore_client, tmdb_client, wiki_client)
        title_detectives_data: TitleDetectivesData = title_detectives.start_quiz(Personality.DEFAULT, chat_session)

        self.assertEqual('Some Movie', title_detectives_data.movie['title'])
        self.assertEqual('audio.mp3', title_detectives_data.speech)

        self.assertEqual('What is the movie?', title_detectives_data.question.question)
        self.assertEqual('hint1', title_detectives_data.question.hint1)
        self.assertEqual('hint2', title_detectives_data.question.hint2)


if __name__ == '__main__':
    unittest.main()
