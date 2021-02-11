import abc
from enum import Enum
from typing import List, Optional, Dict, Any
from typing import TypeVar
from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field


class StreamPrefixEnum(str, Enum):
    position = 'ps'
    geoevent = 'ge'


class TokenData(BaseModel):
    subject: Optional[str] = None
    scopes: List[str] = []


class OAuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


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
    endpoint: str
    id: str
    state: Dict[str, Any]


TIntegrationInformation = TypeVar("TIntegrationInformation", bound=IntegrationInformation)
