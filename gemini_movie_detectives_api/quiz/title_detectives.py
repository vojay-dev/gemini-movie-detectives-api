import logging
from typing import Any

from fastapi import HTTPException
from google.api_core.exceptions import GoogleAPIError
from pydantic_core import from_json
from starlette import status
from vertexai.generative_models import ChatSession

from gemini_movie_detectives_api.gemini import GeminiClient
from gemini_movie_detectives_api.model import TitleDetectivesData, TitleDetectivesResult, TitleDetectivesGeminiQuestion, \
    TitleDetectivesGeminiAnswer, Personality, QuizType
from gemini_movie_detectives_api.speech import SpeechClient
from gemini_movie_detectives_api.template import TemplateManager
from gemini_movie_detectives_api.tmdb import TmdbClient

logger: logging.Logger = logging.getLogger(__name__)


class TitleDetectives:

    def __init__(
        self,
        tmdb_client: TmdbClient,
        template_manager: TemplateManager,
        gemini_client: GeminiClient,
        speech_client: SpeechClient
    ):
        self.tmdb_client = tmdb_client
        self.template_manager = template_manager
        self.gemini_client = gemini_client
        self.speech_client = speech_client

    def start_title_detectives(self, personality: Personality, chat: ChatSession) -> TitleDetectivesData:
        movie = self.tmdb_client.get_random_movie(
            page_min=1,
            page_max=100,
            vote_avg_min=4.0,
            vote_count_min=800
        )

        if not movie:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No movie found with given criteria')

        try:
            prompt = self._generate_question_prompt(
                personality=personality,
                movie_title=movie['title'],
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

            return TitleDetectivesData(
                question=gemini_question,
                movie=movie,
                speech=self.speech_client.synthesize_to_file(gemini_question.question),
                chat=chat
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    def finish_title_detectives(self, answer: str, quiz_data: TitleDetectivesData, chat: ChatSession) -> TitleDetectivesResult:
        try:
            prompt = self._generate_answer_prompt(answer=answer)

            logger.debug('evaluating quiz answer with generated prompt: %s', prompt)
            gemini_reply = self.gemini_client.get_chat_response(chat, prompt)
            gemini_answer = self._parse_gemini_answer(gemini_reply)

            return TitleDetectivesResult(
                question=quiz_data.question,
                movie=quiz_data.movie,
                user_answer=answer,
                result=gemini_answer,
                speech=self.speech_client.synthesize_to_file(gemini_answer.answer)
            )
        except GoogleAPIError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Google API error: {e}')
        except BaseException as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Internal server error: {e}')

    @staticmethod
    def _parse_gemini_question(gemini_reply: str) -> TitleDetectivesGeminiQuestion:
        try:
            return TitleDetectivesGeminiQuestion.model_validate(from_json(gemini_reply))
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    @staticmethod
    def _parse_gemini_answer(gemini_reply: str) -> TitleDetectivesGeminiAnswer:
        try:
            return TitleDetectivesGeminiAnswer.model_validate(from_json(gemini_reply))
        except Exception as e:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}, error: {e}'
            logger.warning(msg)
            raise ValueError(msg)

    def _generate_question_prompt(
        self,
        personality: Personality,
        movie_title: str,
        **kwargs: Any
    ) -> str:
        personality = self.template_manager.render_personality(personality)

        return self.template_manager.render_template(
            quiz_type=QuizType.TITLE_DETECTIVES,
            name='prompt_question',
            personality=personality,
            title=movie_title,
            **kwargs
        )

    def _generate_answer_prompt(self, answer: str) -> str:
        return self.template_manager.render_template(QuizType.TITLE_DETECTIVES, 'prompt_answer', answer=answer)
