import uuid
from pathlib import Path

import emoji
from google.cloud import texttospeech
from google.oauth2.service_account import Credentials


class SpeechClient:

    def __init__(
        self,
        tmp_audio_dir: Path,
        credentials: Credentials,
        language_code: str,
        voice_name: str,
        audio_encoding: texttospeech.AudioEncoding = texttospeech.AudioEncoding.LINEAR16,
        speaking_rate: float = 0.85
    ) -> None:
        self.tmp_audio_dir = tmp_audio_dir
        self.client = texttospeech.TextToSpeechClient(credentials=credentials)

        # noinspection PyTypeChecker
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )

        # noinspection PyTypeChecker
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=speaking_rate
        )

    def synthesize(self, text: str) -> bytes:
        # remove emojis
        text = emoji.replace_emoji(text, replace='')

        # noinspection PyTypeChecker
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
        audio_file_path = f'{self.tmp_audio_dir}/{file_id}.mp3'

        with open(audio_file_path, 'wb') as file:
            file.write(audio_bytes)

        file_url = f'/audio/{file_id}.mp3'
        return file_url
