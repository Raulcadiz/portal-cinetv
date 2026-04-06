"""Pydantic v2 schemas for playlist endpoints."""
from pydantic import BaseModel, Field, field_validator

from src.api.utils.validators import validate_mac


class PlaylistUrlRequest(BaseModel):
    mac: str
    url: str = Field(..., min_length=7)
    name: str | None = None

    @field_validator("mac")
    @classmethod
    def mac_must_be_valid(cls, v: str) -> str:
        return validate_mac(v)

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ClearRequest(BaseModel):
    mac: str

    @field_validator("mac")
    @classmethod
    def mac_must_be_valid(cls, v: str) -> str:
        return validate_mac(v)


class PlaylistMeta(BaseModel):
    """Metadata only — never exposes full m3u8 content in list responses."""
    id: str
    mac: str
    type: str
    name: str | None
    pending_clear: bool

    model_config = {"from_attributes": True}


class PlaylistCreated(BaseModel):
    id: str
    mac: str
    type: str
