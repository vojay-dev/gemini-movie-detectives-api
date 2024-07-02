import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar, Generic

from vertexai.generative_models import ChatSession

from gemini_movie_detectives_api.gemini import GeminiClient
from gemini_movie_detectives_api.imagen import ImagenClient
from gemini_movie_detectives_api.model import Personality
from gemini_movie_detectives_api.speech import SpeechClient
from gemini_movie_detectives_api.storage import FirestoreClient
from gemini_movie_detectives_api.template import TemplateManager
from gemini_movie_detectives_api.tmdb import TmdbClient
from gemini_movie_detectives_api.wiki import WikiClient

logger: logging.Logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class AbstractQuiz(ABC, Generic[T, R]):
    def __init__(
        self,
        template_manager: TemplateManager,
        gemini_client: GeminiClient,
        imagen_client: ImagenClient,
        speech_client: SpeechClient,
        firestore_client: FirestoreClient,
        tmdb_client: TmdbClient,
        wiki_client: WikiClient
    ):
        self.template_manager = template_manager
        self.gemini_client = gemini_client
        self.imagen_client = imagen_client
        self.speech_client = speech_client
        self.firestore_client = firestore_client
        self.tmdb_client = tmdb_client
        self.wiki_client = wiki_client

    @abstractmethod
    def start_quiz(self, personality: Personality, chat: ChatSession) -> T:
        pass

    @abstractmethod
    def finish_quiz(self, answer: Any, quiz_data: T, chat: ChatSession, user_id: Optional[str]) -> R:
        pass
