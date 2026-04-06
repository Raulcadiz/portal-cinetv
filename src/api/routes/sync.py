"""
GET /api/sync — Called by the Android app on startup to fetch the latest configuration.
No authentication required; identified by MAC address.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.sync import SyncEpgItem, SyncPlaylistItem, SyncResponse
from src.api.services import epg_service, playlist_service
from src.core.database import get_db

router = APIRouter()

_MAC_PATTERN = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"


@router.get(
    "/sync",
    response_model=SyncResponse,
    summary="Sync app Android",
    description=(
        "Returns the current configuration for the given MAC address. "
        "The app calls this on startup and periodically. "
        "Responds in <200ms for unknown MACs."
    ),
)
async def sync_device(
    mac: str = Query(..., pattern=_MAC_PATTERN, description="Device MAC address XX:XX:XX:XX:XX:XX"),
    db: AsyncSession = Depends(get_db),
) -> SyncResponse:
    """
    Sync logic:
    1. If any playlist has ``pending_clear=True`` → return ``action=clear`` and reset the flag.
    2. If playlists or EPG exist → return ``action=update`` with full data.
    3. Otherwise → return ``action=none``.
    """
    mac = mac.upper()
    playlists = await playlist_service.list_playlists(db, mac)
    epg = await epg_service.get_epg(db, mac)

    # ── pending clear ─────────────────────────────────────────────────────────
    if any(p.pending_clear for p in playlists):
        await playlist_service.reset_pending_clear(db, mac)
        if epg:
            await epg_service.delete_epg(db, mac)
        return SyncResponse(action="clear")

    # ── update ────────────────────────────────────────────────────────────────
    if playlists or epg:
        return SyncResponse(
            action="update",
            playlists=[
                SyncPlaylistItem(id=p.id, type=p.type, content=p.content, name=p.name)
                for p in playlists
            ],
            epg=SyncEpgItem(id=epg.id, type=epg.type, content=epg.content) if epg else None,
        )

    return SyncResponse(action="none")
