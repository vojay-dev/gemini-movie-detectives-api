import logging

import vertexai
from google.oauth2.service_account import Credentials
from vertexai import generative_models
from vertexai.generative_models import GenerativeModel, ChatSession

logger = logging.getLogger(__name__)


GENERATION_CONFIG = {
    'temperature': 0.6,
    # initialize Gemini with JSON mode enabled, see: https://ai.google.dev/gemini-api/docs/api-overview#json
    'response_mime_type': 'application/json'
}

SAFETY_CONFIG = [
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]


class GeminiClient:

    def __init__(self, project_id: str, location: str, credentials: Credentials, model: str):
        vertexai.init(project=project_id, location=location, credentials=credentials)

        logger.info('loading model: %s', model)
        logger.info('generation config: %s', GENERATION_CONFIG)

        self.model = GenerativeModel(model, safety_settings=SAFETY_CONFIG)

    def start_chat(self) -> ChatSession:
        return self.model.start_chat(response_validation=False)

    @staticmethod
    def get_chat_response(chat: ChatSession, prompt: str) -> str:
        text_response = []
        responses = chat.send_message(prompt, generation_config=GENERATION_CONFIG, stream=True)
        for chunk in responses:
            text_response.append(chunk.text)
        return ''.join(text_response)
