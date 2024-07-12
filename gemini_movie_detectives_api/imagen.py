import logging
import uuid
from pathlib import Path
from typing import Optional

import vertexai
from google.oauth2.service_account import Credentials
from vertexai.preview.vision_models import ImageGenerationModel

logger = logging.getLogger(__name__)


class ImagenClient:

    def __init__(self, project_id: str, location: str, credentials: Credentials, model: str, tmp_images_dir: Path):
        vertexai.init(project=project_id, location=location, credentials=credentials)
        logger.info('loading model: %s', model)

        self.model = ImageGenerationModel.from_pretrained(model)
        self.tmp_images_dir = tmp_images_dir

    def generate_image(self, prompt: str, fallback: Optional[str] = None) -> Optional[str]:
        file_id = uuid.uuid4()
        image_file_path = f'{self.tmp_images_dir}/{file_id}.png'

        if self._try_generate_image(prompt, image_file_path):
            return f'/images/{file_id}.png'

        if fallback and self._try_generate_image(self._get_fallback_prompt(fallback), image_file_path):
            logger.info('used fallback prompt to generate image')
            return f'/images/{file_id}.png'

        return None

    def _try_generate_image(self, prompt: str, image_file_path: str) -> bool:
        try:
            self.model.generate_images(
                prompt=prompt,
                aspect_ratio='3:4',
                number_of_images=1,
                safety_filter_level='block_few',
                person_generation='allow_adult',
            ).images[0].save(image_file_path, include_generation_parameters=False)

            return True
        except Exception as e:
            logger.warning('could not generate image: %s', e)
            return False

    @staticmethod
    def _get_fallback_prompt(fallback: str) -> str:
        return f'Kids friendly movie poster in the context of: {fallback}'
