from enum import Enum

APP_NAME = 'sintegrate'


class TopicEnum(str, Enum):
    observations_unprocessed = f'{APP_NAME}.observations.unprocessed'
    observations_unprocessed_retry_short = f'{APP_NAME}.observations.unprocessed.retry.short'
    observations_unprocessed_retry_long = f'{APP_NAME}.observations.unprocessed.retry.long'
    observations_unprocessed_deadletter = f'{APP_NAME}.observations.unprocessed.deadletter'
    observations_transformed = f'{APP_NAME}.observations.transformed'
    observations_transformed_retry_short = f'{APP_NAME}.observations.transformed.retry.short'
    observations_transformed_retry_long = f'{APP_NAME}.observations.transformed.retry.long'
    observations_transformed_deadletter = f'{APP_NAME}.observations.transformed.deadletter'
