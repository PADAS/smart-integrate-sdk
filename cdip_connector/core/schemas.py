import abc
import logging
from enum import Enum
from typing import List, Optional, Dict, Any, Iterable
from typing import TypeVar
from typing import Union
from uuid import UUID
from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl, ValidationError, validator

logger = logging.getLogger(__name__)


class StreamPrefixEnum(str, Enum):
    position = 'ps'
    geoevent = 'ge'
    message = 'msg'


class DestinationTypes(Enum):
    EarthRanger = 'earth_ranger'
    SmartConnect = 'smart_connect'


class EventTypes(str, Enum):
    glad_alert = 'gfw_glad_alert'
    fire_alert = 'gfw_activefire_alert'
    skylight_entry_alert = 'entry_alert_rep'


class TokenData(BaseModel):
    subject: Optional[str] = None
    scopes: List[str] = []


class OAuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int


class DeviceState(BaseModel):
    device_external_id: str
    state: Optional[Union[str, Dict[str, Any]]] = None


class MetricsEnum(Enum):
    INVOKED = 'invoked'
    ERRORS = 'errors'
    FROM_PROVIDER = 'from_provider'
    TO_CDIP = 'to_cdip'


class RadioStatusEnum(str, Enum):
    """
    Radio Status values.

    online = 'online'
    online_gps = 'online-gps'
    offline = 'offline'
    alarm = 'alarm'
    """


class Location(BaseModel):
    x: float = Field(..., ge=-180.0, le=360.0, title="Longitude in decimal degrees")
    y: float = Field(..., ge=-90.0, le=90.0, title="Latitude in decimal degrees")
    z: float = Field(0.0, title='Altitude in meters.')
    hdop: Optional[int] = None
    vdop: Optional[int] = None


class CDIPBaseModel(BaseModel, abc.ABC):
    id: Optional[int] = None
    device_id: Optional[str] = Field('none', example='901870234', description='A unique identifier of the device associated with this data.')
    name: Optional[str] = Field(None, title='An optional, human-friendly name for the associated device.', example='Security Vehicle A')
    type: Optional[str] = Field('tracking-device', title='Type identifier for the associated device.', example='tracking-device',)
    recorded_at: datetime = Field(..., title='Timestamp for the data, preferrably in ISO format.', example='2021-03-21 12:01:02-0700')
    location: Location
    additional: Optional[Dict[str, Any]] = Field(None, title="Additional Data",
                                                 description="A dictionary of extra data that will be passed to destination systems.")

    owner: str = 'na'
    integration_id: Optional[Union[UUID, str]] = Field(None, title='Integration ID',
                                                  description='The unique ID for the '
                                                              'Smart Integrate Inbound Integration.')

    @staticmethod
    @abc.abstractmethod
    def stream_prefix():
        pass

    @validator('recorded_at')
    def clean_recorded_at(cls, val):

        if not val.tzinfo:
            val = val.replace(tzinfo=timezone.utc)
        return val

class Position(CDIPBaseModel):

    voltage: Optional[float] = Field(None, title='Voltage of tracking device.')
    temperature: Optional[float] = Field(None, title='Tempurature reading at time of Position.')
    radio_status: Optional[RadioStatusEnum] = Field(None, title='Indicate status of a GPS radio.')

    class Config:
        title = 'Position'

        schema_extra = {
            "example": {
                "device_id": '018910980',
                "name": "Logistics Truck A",
                "type": "tracking-device",
                "recorded_at": "2021-03-27 11:15:00+0200",
                "location": {
                    "x": 35.43902,
                    "y": -1.59083
                },
                "additional": {
                    "voltage": "7.4",
                    "fuel_level": 71,
                    "speed": "41 kph",
                }

            }
        }
    @staticmethod
    def stream_prefix():
        return StreamPrefixEnum.position.value


class GeoEvent(CDIPBaseModel):

    title: str = Field(None, title='GeoEvent title',
                       description='Human-friendly title for this GeoEvent')
    event_type: str = Field(None, title='GeoEvent Type',
                            description='Identifies the type of this GeoEvent')

    event_details: Dict[str, Any] = Field(None, title="GeoEvent Details",
                                          description="A dictionary containing details of this GeoEvent.")

    class Config:
        title = 'GeoEvent'

    @staticmethod
    def stream_prefix():
        return StreamPrefixEnum.geoevent.value


class Message(BaseModel):
    owner: str = 'na'
    integration_id: Optional[Union[UUID, str]] = Field(None, title='Integration ID',
                                                  description='The unique ID for the '
                                                              'Smart Integrate Inbound Integration.')
    created_at: datetime
    text: str
    sender: str
    device_ids: List[str]

    @staticmethod
    def stream_prefix():
        return StreamPrefixEnum.message.value


class IntegrationInformation(BaseModel):
    login: str
    password: str
    token: str
    endpoint: HttpUrl
    id: UUID
    state: Optional[Dict[str, Any]] = {}
    device_states: Optional[Dict[str, Any]] = {}


class OutboundConfiguration(BaseModel):
    id: UUID
    type: UUID
    owner: UUID
    endpoint: HttpUrl
    state: Optional[Dict[str, Any]] = {}
    login: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    type_slug: str
    inbound_type_slug: Optional[str] = None
    additional: Optional[Dict[str, Any]] = {}


models_by_stream_type = {
    StreamPrefixEnum.position: Position,
    StreamPrefixEnum.geoevent: GeoEvent
}

TIntegrationInformation = TypeVar("TIntegrationInformation", bound=IntegrationInformation)


def get_validated_objects(objects: Iterable, model: BaseModel) -> (List[BaseModel], List[str]):
    validated = []
    errors = []
    for obj in objects:
        try:
            if isinstance(obj, dict):
                validated.append(model.parse_obj(obj))
            elif isinstance(obj, (str, bytes)):
                validated.append(model.parse_raw(obj))
            else:
                logger.warning(f'ignoring unknown type {type(obj)} for {obj}')
        except ValidationError as ve:
            logger.warning(f'Error {ve} for {obj}')
            errors.append(str(ve))
    return validated, errors
