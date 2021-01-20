from enum import Enum
from typing import Dict, Any, Union, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field


class OAuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class MetricsEnum(Enum):
    INVOKED = 'invoked'
    ERRORS = 'errors'
    FROM_PROVIDER = 'from_provider'
    TO_CDIP = 'to_cdip'


class IntegrationInformation(BaseModel):
    login: str
    password: str
    token: str
    endpoint: str
    id: str
    state: Dict[str, Any]


class Location(BaseModel):
    x: float = Field(..., ge=-180.0, le=360.0)
    y: float = Field(..., ge=-90.0, le=90.0)
    z: float = Field(0.0, ge=0.0)


class CdipPosition(BaseModel):
    device_id: str
    recorded_at: str
    location: Location
    integration_id: Union[int, str, UUID]
    additional: Optional[Dict[str, Any]] = Field(None, title="Additional Data",
                                                 description="A dictionary of extra data that will be passed through.")


TIntegrationInformation = TypeVar("TIntegrationInformation", bound=IntegrationInformation)
