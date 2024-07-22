import logging
from typing import Optional, Any

from fastapi import HTTPException
from google.api_core.exceptions import GoogleAPIError
from pydantic_core import from_json
from starlette import status
from vertexai.generative_models import ChatSession

from gemini_movie_detectives_api.model import Personality, QuizType, \
    TriviaData, TriviaGeminiAnswer, \
    TriviaGeminiQuestion, TriviaResult
from gemini_movie_detectives_api.quiz.base import AbstractQuiz
from gemini_movie_detectives_api.wiki import MovieFacts

logger: logging.Logger = logging.getLogger(__name__)


class Trivia(AbstractQuiz[TriviaData, TriviaResult]):

    def start_quiz(self, personality: Personality, chat: ChatSession) -> TriviaData:
        movie_facts: MovieFacts = self.wiki_client.get_random_movie_facts()
        movie = movie_facts.movie

        try:
            prompt = self._generate_question_prompt(
                personality=personality,
                movie_title=movie['title'],
                context=movie_facts.facts,
                tagline=movie['tagline'],
                overview=movie['overview'],
                genres=', '.join([genre['name'] for genre in movie['genres']]),
                budget=movie['budget'],
                revenue=movie['revenue'],
                average_rating=movie['vote_average'],
                rating_count=movie['vote_count'],
                release_date=movie['release_date'],
                runtime=movie['runtime']
            )

            logger.debug('starting quiz with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_question = self._parse_gemini_question(gemini_reply)

            logger.info('correct answer: %s', gemini_question.correct_answer)

            return TriviaData(
                question=gemini_question,
                movie=movie,
                speech=self.speech_client.synthesize_to_file(gemini_question.question)
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    def finish_quiz(self, answer: int, quiz_data: TriviaData, chat: ChatSession, user_id: Optional[str]) -> TriviaResult:
        try:
            is_correct_answer = answer == quiz_data.question.correct_answer
            user_answer = getattr(quiz_data.question, f'option_{answer}')

            prompt = self._generate_answer_prompt(answer=f'{user_answer} ({answer}) which is {"correct" if is_correct_answer else "incorrect"}')

            logger.debug('evaluating quiz answer with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_answer = self._parse_gemini_answer(gemini_reply)

            points = 3 if is_correct_answer else 0

            if user_id:
                self.firestore_client.inc_games(user_id, QuizType.TRIVIA)
                self.firestore_client.inc_score(user_id, QuizType.TRIVIA, points)

            return TriviaResult(
                question=quiz_data.question,
                movie=quiz_data.movie,
                user_answer=answer,
                result=gemini_answer,
                points=points,
                speech=self.speech_client.synthesize_to_file(gemini_answer.answer)
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    @staticmethod
    def _parse_gemini_question(gemini_reply: str) -> TriviaGeminiQuestion:
        try:
            return TriviaGeminiQuestion.model_validate(from_json(gemini_reply))
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    @staticmethod
    def _parse_gemini_answer(gemini_reply: str) -> TriviaGeminiAnswer:
        try:
            return TriviaGeminiAnswer.model_validate(from_json(gemini_reply), strict=False)
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)


    def _generate_question_prompt(
        self,
        personality: Personality,
        movie_title: str,
        context: str,
        **kwargs: Any
    ) -> str:
        personality = self.template_manager.render_personality(personality)

        return self.template_manager.render_template(
            quiz_type=QuizType.TRIVIA,
            name='prompt_question',
            personality=personality,
            title=movie_title,
            context=context,
            **kwargs
        )

    def _generate_answer_prompt(self, answer: int) -> str:
        return self.template_manager.render_template(QuizType.TRIVIA, 'prompt_answer', answer=answer)
