import unittest
from unittest.mock import Mock

from gemini_movie_detectives_api.model import Personality, TriviaData
from gemini_movie_detectives_api.quiz.trivia import Trivia
from gemini_movie_detectives_api.template import TemplateManager
from gemini_movie_detectives_api.wiki import MovieFacts


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

        wiki_client.get_random_movie_facts.return_value = MovieFacts(movie_title='Some Movie', facts='facts', movie={
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
        })
        gemini_client.get_chat_response.return_value = '{"question": "question", "option_1": "option 1", "option_2": "option 2" , "option_3": "option 3" , "option_4": "option 4", "correct_answer": 4}'
        speech_client.synthesize_to_file.return_value = 'audio.mp3'

        trivia = Trivia(template_manager, gemini_client, imagen_client, speech_client, firestore_client, tmdb_client, wiki_client)
        trivia_data: TriviaData = trivia.start_quiz(Personality.DEFAULT, chat_session)

        self.assertEqual('audio.mp3', trivia_data.speech)
        self.assertEqual('Some Movie', trivia_data.movie['title'])

        self.assertEqual('question', trivia_data.question.question)
        self.assertEqual('option 1', trivia_data.question.option_1)
        self.assertEqual('option 2', trivia_data.question.option_2)
        self.assertEqual('option 3', trivia_data.question.option_3)
        self.assertEqual('option 4', trivia_data.question.option_4)
        self.assertEqual(4, trivia_data.question.correct_answer)


if __name__ == '__main__':
    unittest.main()
