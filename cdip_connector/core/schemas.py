import logging
from enum import Enum
from typing import List, Optional, Dict, Any, Iterable
from typing import TypeVar
from typing import Union
from uuid import UUID
from datetime import datetime, timezone
import uuid

from pydantic import BaseModel, Field, HttpUrl, ValidationError, validator

logger = logging.getLogger(__name__)


class StreamPrefixEnum(str, Enum):
    position = "ps"
    geoevent = "ge"
    message = "msg"
    camera_trap = "ct"
    earthranger_event = "er_event"
    earthranger_patrol = "er_patrol"
    observation = "obv"


class DestinationTypes(Enum):
    EarthRanger = "earth_ranger"
    SmartConnect = "smart_connect"
    WPSWatch = "wps_watch"


class EventTypes(str, Enum):
    glad_alert = "gfw_glad_alert"
    fire_alert = "gfw_activefire_alert"
    skylight_entry_alert = "entry_alert_rep"


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
    z: float = Field(0.0, title="Altitude in meters.")
    hdop: Optional[int] = None
    vdop: Optional[int] = None


class CDIPBaseModel(BaseModel):
    id: Optional[Union[int, uuid.UUID]] = None

    owner: str = "na"
    integration_id: Optional[Union[UUID, str]] = Field(
        None,
        title="Integration ID",
        description="The unique ID for the " "Smart Integrate Inbound Integration.",
    )


class Position(CDIPBaseModel):

    device_id: Optional[str] = Field(
        "none",
        example="901870234",
        description="A unique identifier of the device associated with this data.",
    )
    name: Optional[str] = Field(
        None,
        title="An optional, human-friendly name for the associated device.",
        example="Security Vehicle A",
    )
    type: Optional[str] = Field(
        "tracking-device",
        title="Type identifier for the associated device.",
        example="tracking-device",
    )
    subject_type: Optional[str] = Field(
        None,
        title="Type identifier for the subjected associated to the device.",
        example="giraffe",
    )
    recorded_at: datetime = Field(
        ...,
        title="Timestamp for the data, preferrably in ISO format.",
        example="2021-03-21 12:01:02-0700",
    )
    location: Location
    additional: Optional[Dict[str, Any]] = Field(
        None,
        title="Additional Data",
        description="A dictionary of extra data that will be passed to destination systems.",
    )

    voltage: Optional[float] = Field(None, title="Voltage of tracking device.")
    temperature: Optional[float] = Field(
        None, title="Tempurature reading at time of Position."
    )
    radio_status: Optional[RadioStatusEnum] = Field(
        None, title="Indicate status of a GPS radio."
    )
    observation_type: str = Field(StreamPrefixEnum.position.value, const=True)

    @validator("recorded_at")
    def clean_recorded_at(cls, val):

        if not val.tzinfo:
            val = val.replace(tzinfo=timezone.utc)
        return val

    class Config:
        title = "Position"

        schema_extra = {
            "example": {
                "device_id": "018910980",
                "name": "Logistics Truck A",
                "type": "tracking-device",
                "recorded_at": "2021-03-27 11:15:00+0200",
                "location": {"x": 35.43902, "y": -1.59083},
                "additional": {
                    "voltage": "7.4",
                    "fuel_level": 71,
                    "speed": "41 kph",
                },
            }
        }


class GeoEvent(CDIPBaseModel):

    device_id: Optional[str] = Field(
        "none",
        example="901870234",
        description="A unique identifier of the device associated with this data.",
    )
    recorded_at: datetime = Field(
        ...,
        title="Timestamp for the data, preferrably in ISO format.",
        example="2021-03-21 12:01:02-0700",
    )
    location: Location
    additional: Optional[Dict[str, Any]] = Field(
        None,
        title="Additional Data",
        description="A dictionary of extra data that will be passed to destination systems.",
    )

    title: str = Field(
        None,
        title="GeoEvent title",
        description="Human-friendly title for this GeoEvent",
    )
    event_type: str = Field(
        None, title="GeoEvent Type", description="Identifies the type of this GeoEvent"
    )

    event_details: Dict[str, Any] = Field(
        None,
        title="GeoEvent Details",
        description="A dictionary containing details of this GeoEvent.",
    )
    geometry: Optional[Dict[str, Any]] = Field(
        None,
        title="GeoEvent Geometry",
        description="A dictionary containing details of this GeoEvent geoJSON.",
    )
    observation_type: str = Field(StreamPrefixEnum.geoevent.value, const=True)

    class Config:
        title = "GeoEvent"

    @validator("recorded_at")
    def clean_recorded_at(cls, val):

        if not val.tzinfo:
            val = val.replace(tzinfo=timezone.utc)
        return val


class ERSubject(BaseModel):
    id: Optional[str]
    name: str
    subject_subtype: str
    additional: dict
    is_active: bool


class ERLocation(BaseModel):
    latitude: float
    longitude: float


class ERUpdate(BaseModel):
    message: str
    time: datetime
    user: dict
    type: str


class EREventState(str, Enum):
    active = "active"
    closed = "resolved"
    new = "new"


class EREvent(CDIPBaseModel):
    er_uuid: uuid.UUID = Field(None, alias="id")
    owner: str = "na"
    location: Optional[ERLocation]
    time: datetime
    created_at: datetime
    updated_at: datetime
    serial_number: int
    event_type: str
    priority: int
    priority_label: str
    title: Optional[str]
    state: EREventState
    url: str
    event_details: Dict[str, Any]
    patrols: Optional[List[str]]
    files: Optional[List[dict]]

    uri: Optional[str] = Field(
        "",
        example="https://site.pamdas.org/api/v1.0/activity/events/<id>",
        description="The EarthRanger site where this event was created.",
    )
    device_id: Optional[str] = Field(
        "none",
        example="dev-00011",
        description="A unique identifier of the device/unit associated with this data.",
    )
    integration_id: Optional[Union[UUID, str]] = Field(
        None,
        title="Integration ID",
        description="The unique ID for the " "Smart Integrate Inbound Integration.",
    )
    observation_type: str = Field(StreamPrefixEnum.earthranger_event.value, const=True)

    @validator("state")
    def clean_sender(cls, val):
        if val == "new":
            return "active"
        return val

    @validator("device_id")
    def calculate_device_id(cls, v, values, **kwargs):
        if "event_type" in values:
            return f'eventtype:{values["event_type"]}'
        return v


class Geometry(BaseModel):
    type: str
    coordinates: List[float]


class GeoJson(BaseModel):
    type: str
    geometry: Geometry


class ERPatrolEvent(BaseModel):
    id: str
    event_type: str
    updated_at: datetime
    geojson: Optional[GeoJson]


class ERObservation(BaseModel):
    id: str
    location: ERLocation
    created_at: datetime
    recorded_at: datetime
    source: str
    observation_details: Optional[dict]


class ERPatrolSegment(BaseModel):
    end_location: Optional[ERLocation]
    events: Optional[List[ERPatrolEvent]]
    event_details: Optional[List[EREvent]] = Field(default_factory=list)
    id: str
    leader: Optional[ERSubject]
    patrol_type: str
    schedule_start: Optional[dict]
    schedule_end: Optional[dict]
    start_location: Optional[ERLocation]
    time_range: Optional[dict]
    updates: Optional[List[ERUpdate]]
    track_points: Optional[List[ERObservation]] = Field(default_factory=list)


class ERPatrol(CDIPBaseModel):
    files: Optional[List[dict]]
    id: str
    serial_number: int
    title: Optional[str]
    device_id: Optional[str]
    notes: Optional[List[dict]]
    objective: Optional[str]  # need to test
    patrol_segments: Optional[List[ERPatrolSegment]]  # how to handle multiple ?
    observation_type: str = Field(StreamPrefixEnum.earthranger_patrol.value, const=True)
    state: str
    updates: Optional[List[ERUpdate]]


class Message(BaseModel):
    owner: str = "na"
    integration_id: Optional[Union[UUID, str]] = Field(
        None,
        title="Integration ID",
        description="The unique ID for the " "Smart Integrate Inbound Integration.",
    )
    created_at: datetime
    text: str
    sender: str
    device_ids: List[str]
    observation_type: str = Field(StreamPrefixEnum.message.value, const=True)


class CameraTrap(CDIPBaseModel):

    device_id: Optional[str] = Field(
        "none",
        example="901870234",
        description="A unique identifier of the device associated with this data.",
    )
    name: Optional[str] = Field(
        None,
        title="An optional, human-friendly name for the associated device.",
        example="Camera no. 1",
    )
    type: Optional[str] = Field(
        "camerea-trap",
        title="Type identifier for the associated device.",
        example="camera-trap",
    )
    recorded_at: datetime = Field(
        ...,
        title="Timestamp for the data, preferrably in ISO format.",
        example="2021-03-21 12:01:02-0700",
    )
    location: Location
    additional: Optional[Dict[str, Any]] = Field(
        None,
        title="Additional Data",
        description="A dictionary of extra data that will be passed to destination systems.",
    )
    image_uri: str
    camera_name: Optional[str]
    camera_description: Optional[str]
    camera_version: Optional[str]
    observation_type: str = Field(StreamPrefixEnum.camera_trap.value, const=True)


# TODO: determine purpose for this type. Original intent was for generic model to represent static sensor
class Observation(CDIPBaseModel):
    device_id: str = Field(
        "none",
        example="901870234",
        description="A unique identifier of the device associated with this data.",
    )
    recorded_at: datetime = Field(
        ...,
        title="Timestamp for the data, preferrably in ISO format.",
        example="2021-03-21 12:01:02-0700",
    )
    location: Optional[Location]
    name: Optional[str] = Field(
        None,
        title="An optional, human-friendly name for the associated device.",
        example="Security Vehicle A",
    )
    type: Optional[str] = Field(
        None,
        title="Type identifier for the associated device.",
        example="static-sensor",
    )

    additional: Optional[Dict[str, Any]] = Field(
        None,
        title="Additional Data",
        description="A dictionary of extra data that will be passed to destination systems.",
    )
    observation_type: str = Field(StreamPrefixEnum.observation.value, const=True)

    @validator("recorded_at")
    def clean_recorded_at(cls, val):
        if not val.tzinfo:
            val = val.replace(tzinfo=timezone.utc)
        return val


class IntegrationInformation(BaseModel):
    id: UUID
    login: Optional[str]
    password: Optional[str]
    token: Optional[str]
    endpoint: Optional[HttpUrl]
    type_slug: Optional[str]
    provider: Optional[str]
    state: Optional[Dict[str, Any]] = {}
    device_states: Optional[Dict[str, Any]] = {}
    enabled: bool
    name: str

    @validator("endpoint", pre=True)
    def cleanse_endpoint(cls, endpoint):
        if endpoint == "":
            endpoint = None
        return endpoint


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


class AdditionalDeviceDetail(BaseModel):
    location: Optional[Location]


class Device(BaseModel):
    id: UUID
    external_id: Optional[str]
    name: Optional[str]
    subject_type: Optional[str]
    inbound_configuration: UUID
    additional: Optional[AdditionalDeviceDetail]


models_by_stream_type = {
    StreamPrefixEnum.position: Position,
    StreamPrefixEnum.geoevent: GeoEvent,
    StreamPrefixEnum.earthranger_event: EREvent,
    StreamPrefixEnum.earthranger_patrol: ERPatrol,
    StreamPrefixEnum.camera_trap: CameraTrap,
    StreamPrefixEnum.observation: Observation,
    StreamPrefixEnum.message: Message,
}

TIntegrationInformation = TypeVar(
    "TIntegrationInformation", bound=IntegrationInformation
)


def get_validated_objects(
    objects: Iterable, model: BaseModel
) -> (List[BaseModel], List[str]):
    validated = []
    errors = []
    for obj in objects:
        try:
            if isinstance(obj, dict):
                validated.append(model.parse_obj(obj))
            elif isinstance(obj, (str, bytes)):
                validated.append(model.parse_raw(obj))
            else:
                logger.warning(f"ignoring unknown type {type(obj)} for {obj}")
        except ValidationError as ve:
            logger.warning(f"Error {ve} for {obj}")
            errors.append(str(ve))
    return validated, errors
