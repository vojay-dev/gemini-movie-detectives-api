import uuid
from pathlib import Path

from google.cloud import texttospeech
from google.oauth2.service_account import Credentials

TEMP_AUDIO_DIR = Path("/tmp/movie-detectives/audio")
TEMP_AUDIO_DIR.mkdir(exist_ok=True)


class SpeechClient:

    def __init__(
        self,
        credentials: Credentials,
        language_code: str = 'en-US',
        voice_name: str = 'en-US-Studio-M',
        audio_encoding: texttospeech.AudioEncoding = texttospeech.AudioEncoding.LINEAR16,
        speaking_rate: float = 0.85
    ) -> None:
        self.client = texttospeech.TextToSpeechClient(credentials=credentials)
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=speaking_rate
        )

    def synthesize(self, text: str) -> bytes:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config
        )

        return response.audio_content

    def synthesize_to_file(self, text: str) -> str:
        audio_bytes = self.synthesize(text)
        file_id = str(uuid.uuid4())
        audio_file_path = f'{TEMP_AUDIO_DIR}/{file_id}.mp3'

        with open(audio_file_path, 'wb') as file:
            file.write(audio_bytes)

        file_url = f'/audio/{file_id}.mp3'
        return file_url
