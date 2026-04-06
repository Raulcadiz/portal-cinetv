"""
Portal routes for managing IPTV playlists per device.
All endpoints require JWT authentication.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middlewares.auth import get_current_admin
from src.api.models.admin_user import AdminUser
from src.api.schemas.playlist import (
    ClearRequest,
    PlaylistCreated,
    PlaylistMeta,
    PlaylistUrlRequest,
)
from src.api.services import playlist_service
from src.api.utils.validators import validate_mac
from src.core.config import settings
from src.core.database import get_db

router = APIRouter()

_EXTM3U_HEADER = b"#EXTM3U"
_MAC_PATTERN = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"


# ── Upload file ───────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=201,
    response_model=PlaylistCreated,
    summary="Upload a .m3u8 playlist file for a device",
)
async def upload_playlist(
    mac: str = Form(..., description="Device MAC address XX:XX:XX:XX:XX:XX"),
    name: str = Form(default="", description="Optional playlist name"),
    file: UploadFile = File(..., description=".m3u8 file"),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> PlaylistCreated:
    """
    Validates that:
    - MAC matches the expected format.
    - File starts with ``#EXTM3U``.
    - File does not exceed ``MAX_M3U8_SIZE_MB``.

    Stores the m3u8 content in the database as ``type='file'``.
    """
    try:
        mac = validate_mac(mac)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Size check (read in chunks to avoid loading everything into memory)
    raw = await file.read(settings.max_m3u8_size_bytes + 1)
    if len(raw) > settings.max_m3u8_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {settings.max_m3u8_size_mb} MB.",
        )

    # Header validation
    if not raw.lstrip().startswith(_EXTM3U_HEADER):
        raise HTTPException(
            status_code=400,
            detail="Invalid m3u8 file: missing #EXTM3U header.",
        )

    content = raw.decode("utf-8", errors="replace")
    playlist = await playlist_service.create_playlist(
        db, mac=mac, playlist_type="file", content=content, name=name or None
    )
    return PlaylistCreated(id=playlist.id, mac=mac, type="file")


# ── Save URL ──────────────────────────────────────────────────────────────────

@router.post(
    "/url",
    status_code=201,
    response_model=PlaylistCreated,
    summary="Save a remote playlist URL for a device",
)
async def save_playlist_url(
    body: PlaylistUrlRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> PlaylistCreated:
    """Stores a remote m3u8 URL for *mac* as ``type='url'``."""
    playlist = await playlist_service.create_playlist(
        db, mac=body.mac, playlist_type="url", content=body.url, name=body.name
    )
    return PlaylistCreated(id=playlist.id, mac=body.mac, type="url")


# ── List playlists ────────────────────────────────────────────────────────────

@router.get(
    "/playlists",
    response_model=list[PlaylistMeta],
    summary="List playlists for a device",
)
async def list_playlists(
    mac: str = Query(..., pattern=_MAC_PATTERN),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> list[PlaylistMeta]:
    """Returns playlist metadata (no full m3u8 content) for the given MAC."""
    playlists = await playlist_service.list_playlists(db, mac.upper())
    return [PlaylistMeta.model_validate(p) for p in playlists]


# ── Delete single playlist ────────────────────────────────────────────────────

@router.delete(
    "/playlist/{playlist_id}",
    summary="Delete a specific playlist by ID",
)
async def delete_playlist(
    playlist_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """Deletes the playlist with *playlist_id*. Returns 404 if not found."""
    deleted = await playlist_service.delete_playlist(db, playlist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"deleted": True}


# ── Pending clear ─────────────────────────────────────────────────────────────

@router.delete(
    "/clear",
    summary="Mark all playlists + EPG as pending clear for a device",
)
async def clear_device(
    body: ClearRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """
    Sets ``pending_clear=True`` on all playlists for *mac* and removes its EPG.
    The Android app receives ``action=clear`` on next sync and wipes local data.
    """
    await playlist_service.set_pending_clear(db, body.mac)
    return {"status": "pending_clear_set"}
