"""Pydantic v2 schemas for the sync endpoint."""
from pydantic import BaseModel


class SyncPlaylistItem(BaseModel):
    id: str
    type: str
    content: str
    name: str | None = None


class SyncEpgItem(BaseModel):
    id: str
    type: str
    content: str


class SyncResponse(BaseModel):
    action: str  # 'none' | 'clear' | 'update'
    playlists: list[SyncPlaylistItem] | None = None
    epg: SyncEpgItem | None = None
