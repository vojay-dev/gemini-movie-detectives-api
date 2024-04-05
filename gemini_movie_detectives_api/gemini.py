import logging
import re

import vertexai
from google.oauth2.service_account import Credentials
from vertexai.generative_models import GenerativeModel, ChatSession

from .config import GENERATION_CONFIG

logger = logging.getLogger(__name__)


class GeminiClient:

    def __init__(self, project_id: str, location: str, credentials: Credentials, model: str = 'gemini-1.0-pro'):
        vertexai.init(project=project_id, location=location, credentials=credentials)

        logger.info('loading model: %s', model)
        logger.info('generation config: %s', GENERATION_CONFIG)
        self.model = GenerativeModel(model)

    def start_chat(self) -> ChatSession:
        return self.model.start_chat()

    @staticmethod
    def get_chat_response(chat: ChatSession, prompt: str) -> str:
        text_response = []
        responses = chat.send_message(prompt, generation_config=GENERATION_CONFIG, stream=True)
        for chunk in responses:
            text_response.append(chunk.text)
        return ''.join(text_response)

    @staticmethod
    def parse_gemini_question(gemini_reply: str):
        result = re.findall(r'[^:]+: ([^\n]+)', gemini_reply, re.MULTILINE)
        if len(result) != 3:
            msg = f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}'
            logger.warning(msg)
            raise ValueError(msg)

        question = result[0]
        hint1 = result[1]
        hint2 = result[2]

        return {
            'question': question,
            'hint1': hint1,
            'hint2': hint2
        }

    @staticmethod
    def parse_gemini_answer(gemini_reply: str):
        points = None
        answer = None

        for line in gemini_reply.splitlines():
            if line.startswith('Points:'):
                points = line[7:].lstrip().rstrip()
            elif line.startswith('Answer:'):
                answer = line[7:].lstrip().rstrip()

        if not points or not answer:
            raise ValueError(f'Gemini replied with an unexpected format. Gemini reply: {gemini_reply}')

        return {
            'points': points,
            'answer': answer
        }
