from enum import Enum

APP_NAME = 'sintegrate'


class TopicEnum(str, Enum):
    observations_unprocessed = f'{APP_NAME}.observations.unprocessed'
    observations_transformed = f'{APP_NAME}.observations.transformed'
    observations_transformed_retry_short = f'{APP_NAME}.observations.transformed.retry.short'
    observations_transformed_retry_long = f'{APP_NAME}.observations.transformed.retry.long'
    observations_transformed_deadletter = f'{APP_NAME}.observations.transformed.deadletter'


class CloudStorageTypeEnum(str, Enum):
    google = 'google'
    local = 'local'
