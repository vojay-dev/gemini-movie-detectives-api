import logging
from typing import Optional

from fastapi import HTTPException
from google.api_core.exceptions import GoogleAPIError
from pydantic_core import from_json
from starlette import status
from vertexai.generative_models import ChatSession

from gemini_movie_detectives_api.model import Personality, QuizType, \
    BttfTriviaData, BttfTriviaGeminiQuestion, BttfTriviaGeminiAnswer, BttfTriviaResult
from gemini_movie_detectives_api.quiz.base import AbstractQuiz

logger: logging.Logger = logging.getLogger(__name__)


class BttfTrivia(AbstractQuiz[BttfTriviaData, BttfTriviaResult]):

    def start_quiz(self, personality: Personality, chat: ChatSession) -> BttfTriviaData:
        context = self.wiki_client.get_random_bttf_facts()

        try:
            prompt = self._generate_question_prompt(
                personality=personality,
                context=context
            )

            logger.debug('starting quiz with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_question = self._parse_gemini_question(gemini_reply)

            logger.info('correct answer: %s', gemini_question.correct_answer)

            return BttfTriviaData(
                question=gemini_question,
                speech=self.speech_client.synthesize_to_file(gemini_question.question)
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    def finish_quiz(self, answer: int, quiz_data: BttfTriviaData, chat: ChatSession, user_id: Optional[str]) -> BttfTriviaResult:
        try:
            is_correct_answer = answer == quiz_data.question.correct_answer
            user_answer = getattr(quiz_data.question, f'option_{answer}')

            prompt = self._generate_answer_prompt(answer=f'{user_answer} ({answer}) which is {"correct" if is_correct_answer else "incorrect"}')

            logger.debug('evaluating quiz answer with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_answer = self._parse_gemini_answer(gemini_reply)

            points = 3 if is_correct_answer else 0

            if user_id:
                self.firestore_client.inc_games(user_id, QuizType.BTTF_TRIVIA)
                self.firestore_client.inc_score(user_id, QuizType.BTTF_TRIVIA, points)

            return BttfTriviaResult(
                question=quiz_data.question,
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
    def _parse_gemini_question(gemini_reply: str) -> BttfTriviaGeminiQuestion:
        try:
            return BttfTriviaGeminiQuestion.model_validate(from_json(gemini_reply))
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    @staticmethod
    def _parse_gemini_answer(gemini_reply: str) -> BttfTriviaGeminiAnswer:
        try:
            return BttfTriviaGeminiAnswer.model_validate(from_json(gemini_reply), strict=False)
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    def _generate_question_prompt(
        self,
        personality: Personality,
        context: str
    ) -> str:
        personality = self.template_manager.render_personality(personality)

        return self.template_manager.render_template(
            quiz_type=QuizType.BTTF_TRIVIA,
            name='prompt_question',
            personality=personality,
            context=context
        )

    def _generate_answer_prompt(self, answer: int) -> str:
        return self.template_manager.render_template(QuizType.BTTF_TRIVIA, 'prompt_answer', answer=answer)
