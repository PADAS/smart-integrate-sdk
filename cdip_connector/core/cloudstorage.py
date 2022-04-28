import logging
import os
from enum import Enum
from io import BytesIO
from abc import ABC, abstractmethod

from google.cloud import storage

from cdip_connector.core import cdip_settings

logger = logging.getLogger(__name__)

class CloudStorageTypeEnum(str, Enum):
    google = 'google'
    local = 'local'


# TODO: Centralize this so both cdip-api and cdip-routing can reference same code
class CloudStorage(ABC):

    @abstractmethod
    def download(self):
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


