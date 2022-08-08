import io
import logging
import os
import pathlib
import tempfile
from abc import ABC, abstractmethod
from enum import Enum
from io import BytesIO

from PIL import Image
from google.cloud import storage
from google.cloud.storage import Blob

from cdip_connector.core import cdip_settings

logger = logging.getLogger(__name__)

class CloudStorageTypeEnum(str, Enum):
    google = 'google'
    local = 'local'


class CloudStorage(ABC):

    @abstractmethod
    def download(self):
        ...

    @abstractmethod
    def upload(self):
        ...

    @abstractmethod
    def check_exists(self):
        ...

    @abstractmethod
    def remove(self):
        ...


class GoogleCouldStorage(CloudStorage):
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cdip_settings.GOOGLE_APPLICATION_CREDENTIALS
        try:
            self.client = storage.Client()
            self.bucket = self.client.get_bucket(cdip_settings.BUCKET_NAME)
        except Exception as e:
            logger.exception(f'Exception while initializing Google CLoud Storage: {e} \n'
                             f'Ensure GOOGLE_APPLICATION_CREDENTIALS are specified in this environment')

    def download(self, file_name):
        file = None
        blob = self.bucket.get_blob(file_name)
        if blob:
            file = BytesIO()
            blob.download_to_file(file)
            file.seek(0)
            file.name = file_name
        else:
            logger.warning(f'{file_name} not found in cloud storage')
        return file

    def upload(self, file: bytes, file_name: str) -> str:
        # first check if image has been uploaded previously
        blob = self.bucket.get_blob(file_name)
        if not blob:
            blob = Blob(file_name, self.bucket)
            file_extension = pathlib.Path(file_name).suffix
            blob.upload_from_string(data=file, content_type=file_extension)
        else:
            logger.info(f'{file_name} found in cloud storage, skipping upload')
        return file_name

    def check_exists(self, file_name: str) -> bool:
        exists = storage.Blob(bucket=self.bucket, name=file_name).exists(self.client)
        return exists

    def remove(self, file):
        # TODO: remove from cloud storage? Or upload with TTL setting?
        try:
            file.close()
        except Exception as e:
            logger.warning(f'failed to close file with exception: {e}')


class LocalStorage(CloudStorage):
    def download(self, file_path):
        file = open(file_path, "rb")
        return file

    def upload(self, file: bytes, file_name: str) -> str:
        # deleting to occur in cdip-routing when image is dispatched
        file_extension = pathlib.Path(file_name).suffix
        temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=file_extension)
        image_uri = temp_file.name
        logger.debug(f'Temp image name: {image_uri}')

        with Image.open(io.BytesIO(file)) as img:
            img.save(image_uri)

        return image_uri

    def check_exists(self, file_name: str) -> bool:
        # TODO: currently not in use but implemented for contract. temp file name path will create a new one each time
        path = pathlib.Path(file_name)
        exists = path.is_file()
        return exists

    def remove(self, file):
        try:
            file.close()
            os.remove(file.name)
        except Exception as e:
            logger.warning(f'failed to remove {file} with exception: {e}')


def get_cloud_storage():
    if str.lower(cdip_settings.CLOUD_STORAGE_TYPE) == CloudStorageTypeEnum.google.value:
        return GoogleCouldStorage()
    else:
        return LocalStorage()


