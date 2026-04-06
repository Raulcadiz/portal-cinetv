"""Business logic for EPG management."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.device_epg import DeviceEpg


async def upsert_epg(
    db: AsyncSession,
    mac: str,
    epg_type: str,
    content: str,
) -> DeviceEpg:
    """
    Insert or replace the EPG for *mac*.
    Only one EPG per MAC is allowed — existing records are deleted before inserting.
    """
    existing_result = await db.execute(
        select(DeviceEpg).where(DeviceEpg.mac == mac)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()

    epg = DeviceEpg(id=str(uuid.uuid4()), mac=mac, type=epg_type, content=content)
    db.add(epg)
    await db.flush()
    return epg


async def get_epg(db: AsyncSession, mac: str) -> DeviceEpg | None:
    """Return the EPG for *mac*, or ``None`` if not configured."""
    result = await db.execute(select(DeviceEpg).where(DeviceEpg.mac == mac))
    return result.scalar_one_or_none()


async def delete_epg(db: AsyncSession, mac: str) -> bool:
    """Delete EPG for *mac*. Returns ``True`` if deleted, ``False`` if none existed."""
    epg = await get_epg(db, mac)
    if epg is None:
        return False
    await db.delete(epg)
    return True
