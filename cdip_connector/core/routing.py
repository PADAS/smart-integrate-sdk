from enum import Enum

APP_NAME = 'sintegrate'


class TopicEnum(str, Enum):
    observations_unprocessed = f'{APP_NAME}.observations.unprocessed'
    observations_transformed = f'{APP_NAME}.observations.transformed'
    #TODO: These can be removed once formally on single topic
    positions_unprocessed = f'{APP_NAME}.positions.unprocessed'
    positions_transformed = f'{APP_NAME}.positions.transformed'
    geoevent_unprocessed = f'{APP_NAME}.geoevent.unprocessed'
    geoevent_transformed = f'{APP_NAME}.geoevent.transformed'
    message_unprocessed = f'{APP_NAME}.message.unprocessed'
    message_transformed = f'{APP_NAME}.message.transformed'
    cameratrap_unprocessed = f'{APP_NAME}.cameratrap.unprocessed'
    cameratrap_transformed = f'{APP_NAME}.cameratrap.transformed'


class CloudStorageTypeEnum(str, Enum):
    google = 'google'
    local = 'local'
