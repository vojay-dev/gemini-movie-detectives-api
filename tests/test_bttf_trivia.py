import unittest
from unittest.mock import Mock

from gemini_movie_detectives_api.model import Personality, BttfTriviaData
from gemini_movie_detectives_api.quiz.bttf_trivia import BttfTrivia
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

        wiki_client.get_random_bttf_facts.return_value = 'facts'
        gemini_client.get_chat_response.return_value = '{"question": "question", "option_1": "option 1", "option_2": "option 2" , "option_3": "option 3" , "option_4": "option 4", "correct_answer": 4}'
        speech_client.synthesize_to_file.return_value = 'audio.mp3'

        bttf_trivia = BttfTrivia(template_manager, gemini_client, imagen_client, speech_client, firestore_client, tmdb_client, wiki_client)
        bttf_trivia_data: BttfTriviaData = bttf_trivia.start_quiz(Personality.DEFAULT, chat_session)

        self.assertEqual('audio.mp3', bttf_trivia_data.speech)

        self.assertEqual('question', bttf_trivia_data.question.question)
        self.assertEqual('option 1', bttf_trivia_data.question.option_1)
        self.assertEqual('option 2', bttf_trivia_data.question.option_2)
        self.assertEqual('option 3', bttf_trivia_data.question.option_3)
        self.assertEqual('option 4', bttf_trivia_data.question.option_4)
        self.assertEqual(4, bttf_trivia_data.question.correct_answer)


if __name__ == '__main__':
    unittest.main()
