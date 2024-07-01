import logging
import uuid
from pathlib import Path

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

    def generate_image(self, prompt: str) -> str | None:
        # noinspection PyBroadException
        try:
            file_id = str(uuid.uuid4())
            image_file_path = f'{self.tmp_images_dir}/{file_id}.png'

            self.model.generate_images(
                prompt=prompt,
                aspect_ratio='3:4',
                number_of_images=1,
                safety_filter_level='block_few',
                person_generation='allow_adult',
            ).images[0].save(image_file_path, include_generation_parameters=False)

            file_url = f'/images/{file_id}.png'
            return file_url
        except BaseException as e:
            logger.warning('could not generate image: %s', e)
            return None
