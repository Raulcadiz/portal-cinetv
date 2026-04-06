"""Business logic for playlist management."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.device_epg import DeviceEpg
from src.api.models.device_playlist import DevicePlaylist


async def create_playlist(
    db: AsyncSession,
    mac: str,
    playlist_type: str,
    content: str,
    name: str | None = None,
) -> DevicePlaylist:
    """Persist a new playlist and return it."""
    playlist = DevicePlaylist(mac=mac, type=playlist_type, content=content, name=name)
    db.add(playlist)
    await db.flush()
    return playlist


async def list_playlists(db: AsyncSession, mac: str) -> list[DevicePlaylist]:
    """Return all playlists for *mac*, ordered by creation date."""
    result = await db.execute(
        select(DevicePlaylist)
        .where(DevicePlaylist.mac == mac)
        .order_by(DevicePlaylist.created_at)
    )
    return list(result.scalars().all())


async def get_playlist(db: AsyncSession, playlist_id: str) -> DevicePlaylist | None:
    """Fetch a single playlist by ID."""
    result = await db.execute(
        select(DevicePlaylist).where(DevicePlaylist.id == playlist_id)
    )
    return result.scalar_one_or_none()


async def delete_playlist(db: AsyncSession, playlist_id: str) -> bool:
    """Delete playlist by ID. Returns ``True`` if deleted, ``False`` if not found."""
    playlist = await get_playlist(db, playlist_id)
    if playlist is None:
        return False
    await db.delete(playlist)
    return True


async def set_pending_clear(db: AsyncSession, mac: str) -> int:
    """
    Mark *all* playlists for *mac* as ``pending_clear=True`` and delete the EPG.
    Returns the number of playlists updated.
    """
    result = await db.execute(
        update(DevicePlaylist)
        .where(DevicePlaylist.mac == mac)
        .values(pending_clear=True)
    )
    # Delete EPG for this MAC as well
    epg_result = await db.execute(
        select(DeviceEpg).where(DeviceEpg.mac == mac)
    )
    epg = epg_result.scalar_one_or_none()
    if epg:
        await db.delete(epg)
    return result.rowcount


async def reset_pending_clear(db: AsyncSession, mac: str) -> None:
    """Reset ``pending_clear=False`` for all playlists of *mac* after the app ACKs."""
    await db.execute(
        update(DevicePlaylist)
        .where(DevicePlaylist.mac == mac)
        .values(pending_clear=False)
    )
