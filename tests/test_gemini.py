import unittest

from gemini_movie_detectives_api.gemini import GeminiClient


class TestGemini(unittest.TestCase):

    def test_parse_gemini_question(self):
        gemini_reply = """
            Question: I am looking for a great movie!
            Hint1: It is a movie.
            Hint2: M_ovie
        """
        gemini_question = GeminiClient.parse_gemini_question(gemini_reply)

        self.assertEqual(gemini_question.question, 'I am looking for a great movie!')
        self.assertEqual(gemini_question.hint1, 'It is a movie.')
        self.assertEqual(gemini_question.hint2, 'M_ovie')

        # Parser should be language agnostic
        gemini_reply = """
            Meine Frage ist: Wie heißt dieser tolle Film?
            Der erste Hinweis: Es ist ein Film aus dem Jahr 2024.
            Zweiter Hinweis: Fi_m
        """
        gemini_question = GeminiClient.parse_gemini_question(gemini_reply)

        self.assertEqual(gemini_question.question, 'Wie heißt dieser tolle Film?')
        self.assertEqual(gemini_question.hint1, 'Es ist ein Film aus dem Jahr 2024.')
        self.assertEqual(gemini_question.hint2, 'Fi_m')

    def test_parse_gemini_answer(self):
        gemini_reply = """
            Points: 4711
            Answer: You got it right!
        """
        gemini_answer = GeminiClient.parse_gemini_answer(gemini_reply)

        self.assertEqual(gemini_answer.answer, 'You got it right!')
        self.assertEqual(gemini_answer.points, 4711)


if __name__ == '__main__':
    unittest.main()
