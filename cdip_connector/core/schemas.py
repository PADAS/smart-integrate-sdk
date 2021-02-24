import abc
import logging
from enum import Enum
from typing import List, Optional, Dict, Any, Iterable
from typing import TypeVar
from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, ValidationError

logger = logging.getLogger(__name__)


class StreamPrefixEnum(str, Enum):
    position = 'ps'
    geoevent = 'ge'


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


class DeviceState(BaseModel):
    device_external_id: str
    end_state: str


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
    x: float = Field(..., ge=-180.0, le=360.0)
    y: float = Field(..., ge=-90.0, le=90.0)
    z: float = Field(0.0)
    hdop: Optional[int] = None
    vdop: Optional[int] = None


class CDIPBaseModel(BaseModel, abc.ABC):
    id: Optional[int] = None
    device_id: Optional[str] = 'none'
    name: Optional[str] = None
    type: Optional[str] = None
    recorded_at: str
    location: Location
    additional: Optional[Dict[str, Any]] = Field(None, title="Additional Data",
                                                 description="A dictionary of extra data that will be passed through.")

    owner: str = 'na'
    integration_id: Union[int, str, UUID] = Field(None, title='Integration ID',
                                                  description='The unique ID for the '
                                                              'Smart Integrate Inbound Integration.')

    @staticmethod
    @abc.abstractmethod
    def stream_prefix():
        pass


class Position(CDIPBaseModel):

    voltage: Optional[float] = None
    temperature: Optional[float] = None
    radio_status: Optional[RadioStatusEnum]

    class Config:
        title = 'Position'

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


class IntegrationInformation(BaseModel):
    login: str
    password: str
    token: str
    endpoint: HttpUrl
    id: UUID
    state: Optional[Dict[str, Any]] = {}
    device_states: Optional[List[DeviceState]] = []


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
    inbound_type_slug: str
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
