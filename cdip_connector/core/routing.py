from enum import Enum

APP_NAME = 'sintegrate'


class TopicEnum(str, Enum):
    positions_unprocessed = f'{APP_NAME}.positions.unprocessed'
    positions_transformed = f'{APP_NAME}.positions.transformed'
    geoevent_unprocessed = f'{APP_NAME}.geoevent.unprocessed'
    geoevent_transformed = f'{APP_NAME}.geoevent.transformed'
    message_unprocessed = f'{APP_NAME}.message.unprocessed'
    message_transformed = f'{APP_NAME}.message.transformed'
    cameratrap_unprocessed = f'{APP_NAME}.cameratrap.unprocessed'
    cameratrap_transformed = f'{APP_NAME}.cameratrap.transformed'


class CloudStorage(str, Enum):
    google = 'google'
    local = 'local'
