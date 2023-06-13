from typing import List, Optional, Dict, Any
from typing import Union
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
from .common import *
from .v1 import CDIPBaseModel


class StreamPrefixEnum(str, Enum):
    event = "ev"
    attachment = "att"


class Location(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, title="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180.0, le=360.0, title="Longitude in decimal degrees")
    alt: float = Field(0.0, title="Altitude in meters.")
    hdop: Optional[int] = None
    vdop: Optional[int] = None


class Event(CDIPBaseModel):

    source_id: str = Field(
        "none",
        example="901870234",
        description="A unique identifier of the source associated with this data (f.k.a. device).",
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
        title="Event title",
        description="Human-friendly title for this GeoEvent",
    )
    event_type: str = Field(
        None, title="Event Type", description="Identifies the type of this GeoEvent"
    )

    event_details: Dict[str, Any] = Field(
        None,
        title="Event Details",
        description="A dictionary containing details of this GeoEvent.",
    )
    geometry: Optional[Dict[str, Any]] = Field(
        None,
        title="Event Geometry",
        description="A dictionary containing details of this GeoEvent geoJSON.",
    )
    observation_type: str = Field(StreamPrefixEnum.event.value, const=True)

    class Config:
        title = "GeoEvent"

    @validator("recorded_at", allow_reuse=True)
    def clean_recorded_at(cls, val):

        if not val.tzinfo:
            val = val.replace(tzinfo=timezone.utc)
        return val


class Attachment(CDIPBaseModel):
    source_id: str = Field(
        "none",
        example="901870234",
        description="A unique identifier of the source associated with this data (f.k.a. device).",
    )
    related_to: Optional[Union[UUID, str]] = Field(
        None,
        title="Related Object - Gundi ID",
        description="The Gundi ID of the related object this file is being attached to",
    )
    file_path: str
    observation_type: str = Field(StreamPrefixEnum.attachment.value, const=True)


models_by_stream_type = {
    StreamPrefixEnum.event: Event,
    StreamPrefixEnum.attachment: Attachment,
}
