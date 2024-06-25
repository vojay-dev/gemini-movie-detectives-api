import logging

from gemini_movie_detectives_api.gemini import GeminiClient
from gemini_movie_detectives_api.model import SequelSaladData, SequelSaladGeminiQuestion, \
    SequelSaladResult, SequelSaladGeminiAnswer
from gemini_movie_detectives_api.speech import SpeechClient
from gemini_movie_detectives_api.template import TemplateManager

logger: logging.Logger = logging.getLogger(__name__)


class SequelSalad:

    def __init__(
        self,
        template_manager: TemplateManager,
        gemini_client: GeminiClient,
        speech_client: SpeechClient
    ):
        self.template_manager = template_manager
        self.gemini_client = gemini_client
        self.speech_client = speech_client

    @staticmethod
    def start_sequel_salad() -> SequelSaladData:
        return SequelSaladData(
            question=SequelSaladGeminiQuestion(
                franchise='Back to the Future',
                sequel_plot='Marty McFly travels to the future to save his children from disaster'
            ),
            speech=''
        )

    @staticmethod
    def finish_sequel_salad(answer: str, quiz_data: SequelSaladData) -> SequelSaladResult:
        return SequelSaladResult(
            question=quiz_data.question,
            franchise=quiz_data.question.franchise,
            user_answer=answer,
            result=SequelSaladGeminiAnswer(
                points=1,
                answer='Back to the Future Part V'
            ),
            speech=''
        )
