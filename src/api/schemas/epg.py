"""Pydantic v2 schemas for EPG endpoints."""
from pydantic import BaseModel, Field, field_validator

from src.api.utils.validators import validate_mac


class EpgUrlRequest(BaseModel):
    mac: str
    url: str = Field(..., min_length=7)

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


class EpgDeleteRequest(BaseModel):
    mac: str

    @field_validator("mac")
    @classmethod
    def mac_must_be_valid(cls, v: str) -> str:
        return validate_mac(v)


class EpgInfo(BaseModel):
    id: str
    mac: str
    type: str

    model_config = {"from_attributes": True}
