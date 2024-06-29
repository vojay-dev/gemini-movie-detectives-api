import logging
import random
from typing import Any, Optional

from fastapi import HTTPException
from google.api_core.exceptions import GoogleAPIError
from pydantic_core import from_json
from starlette import status
from vertexai.generative_models import ChatSession

from gemini_movie_detectives_api.gemini import GeminiClient
from gemini_movie_detectives_api.imagen import ImagenClient
from gemini_movie_detectives_api.model import SequelSaladData, SequelSaladGeminiQuestion, \
    SequelSaladResult, SequelSaladGeminiAnswer, Personality, QuizType
from gemini_movie_detectives_api.speech import SpeechClient
from gemini_movie_detectives_api.storage import FirestoreClient
from gemini_movie_detectives_api.template import TemplateManager

logger: logging.Logger = logging.getLogger(__name__)


class SequelSalad:

    def __init__(
        self,
        template_manager: TemplateManager,
        gemini_client: GeminiClient,
        imagen_client: ImagenClient,
        speech_client: SpeechClient,
        firestore_client: FirestoreClient
    ):
        self.template_manager = template_manager
        self.gemini_client = gemini_client
        self.imagen_client = imagen_client
        self.speech_client = speech_client
        self.firestore_client = firestore_client

    def start_sequel_salad(self, personality: Personality, chat: ChatSession) -> SequelSaladData:
        try:
            franchise = random.choice(self.firestore_client.get_franchises())
            prompt = self._generate_question_prompt(
                personality=personality,
                franchise=franchise
            )

            logger.debug('starting quiz with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_question = self._parse_gemini_question(gemini_reply)

            poster = self.imagen_client.generate_image(gemini_question.poster_prompt)

            return SequelSaladData(
                question=gemini_question,
                franchise=franchise,
                speech=self.speech_client.synthesize_to_file(gemini_question.sequel_plot),
                poster=poster
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    def finish_sequel_salad(self, answer: str, quiz_data: SequelSaladData, chat: ChatSession, user_id: Optional[str]) -> SequelSaladResult:
        try:
            prompt = self._generate_answer_prompt(answer=answer)

            logger.debug('evaluating quiz answer with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_answer = self._parse_gemini_answer(gemini_reply)

            if user_id:
                self.firestore_client.inc_games(user_id, QuizType.SEQUEL_SALAD)
                self.firestore_client.inc_score(user_id, QuizType.SEQUEL_SALAD, gemini_answer.points)

            return SequelSaladResult(
                question=quiz_data.question,
                franchise=quiz_data.franchise,
                user_answer=answer,
                result=gemini_answer,
                speech=self.speech_client.synthesize_to_file(gemini_answer.answer)
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    @staticmethod
    def _parse_gemini_question(gemini_reply: str) -> SequelSaladGeminiQuestion:
        try:
            return SequelSaladGeminiQuestion.model_validate(from_json(gemini_reply))
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    @staticmethod
    def _parse_gemini_answer(gemini_reply: str) -> SequelSaladGeminiAnswer:
        try:
            return SequelSaladGeminiAnswer.model_validate(from_json(gemini_reply))
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    def _generate_question_prompt(self, personality: Personality, **kwargs: Any) -> str:
        personality = self.template_manager.render_personality(personality)

        return self.template_manager.render_template(
            quiz_type=QuizType.SEQUEL_SALAD,
            name='prompt_question',
            personality=personality,
            **kwargs
        )

    def _generate_answer_prompt(self, answer: str) -> str:
        return self.template_manager.render_template(QuizType.SEQUEL_SALAD, 'prompt_answer', answer=answer)
