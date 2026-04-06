"""
CRUD de listas IPTV de usuario (URL directa o Xtream Codes).
"""
import json
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.user_list import UserList
from src.api.services.m3u_parser import (
    build_xtream_m3u_url,
    fetch_url_content,
    parse_groups,
)


# ── Lectura ────────────────────────────────────────────────────────────────────

async def get_user_lists(device_id: str, db: AsyncSession) -> List[UserList]:
    result = await db.execute(
        select(UserList)
        .where(UserList.device_id == device_id)
        .order_by(UserList.created_at)
    )
    return list(result.scalars().all())


async def get_list(list_id: str, device_id: str, db: AsyncSession) -> UserList | None:
    result = await db.execute(
        select(UserList).where(UserList.id == list_id, UserList.device_id == device_id)
    )
    return result.scalar_one_or_none()


# ── Creación ──────────────────────────────────────────────────────────────────

async def add_url_list(
    device_id: str, name: str, url: str, db: AsyncSession
) -> UserList:
    ul = UserList(
        id=str(uuid.uuid4()),
        device_id=device_id,
        name=name or url,
        list_type="url",
        url=url,
    )
    db.add(ul)
    await db.commit()
    await db.refresh(ul)
    return ul


async def add_xtream_list(
    device_id: str,
    name: str,
    server: str,
    username: str,
    password: str,
    db: AsyncSession,
) -> UserList:
    ul = UserList(
        id=str(uuid.uuid4()),
        device_id=device_id,
        name=name or server,
        list_type="xtream",
        xtream_server=server.rstrip("/"),
        xtream_user=username,
        xtream_pass=password,
    )
    db.add(ul)
    await db.commit()
    await db.refresh(ul)
    return ul


async def add_file_list(
    device_id: str, name: str, content: str, db: AsyncSession
) -> UserList:
    ul = UserList(
        id=str(uuid.uuid4()),
        device_id=device_id,
        name=name or "Lista subida",
        list_type="file",
        content=content,
    )
    db.add(ul)
    await db.commit()
    await db.refresh(ul)
    return ul


# ── Eliminación ───────────────────────────────────────────────────────────────

async def delete_list(list_id: str, device_id: str, db: AsyncSession) -> bool:
    ul = await get_list(list_id, device_id, db)
    if not ul:
        return False
    await db.delete(ul)
    await db.commit()
    return True


# ── Grupos ────────────────────────────────────────────────────────────────────

async def get_list_groups(list_id: str, device_id: str, db: AsyncSession) -> List[str]:
    """Obtiene los grupos disponibles en una lista M3U (descargando si hace falta)."""
    ul = await get_list(list_id, device_id, db)
    if not ul:
        return []

    try:
        if ul.list_type == "url" and ul.url:
            content = await fetch_url_content(ul.url)
            return parse_groups(content)
        elif ul.list_type == "xtream":
            m3u_url = build_xtream_m3u_url(
                ul.xtream_server, ul.xtream_user, ul.xtream_pass
            )
            content = await fetch_url_content(m3u_url)
            return parse_groups(content)
        elif ul.list_type == "file" and ul.content:
            return parse_groups(ul.content)
    except Exception:
        pass

    return []


async def set_selected_groups(
    list_id: str, device_id: str, groups: List[str], db: AsyncSession
) -> bool:
    """Guarda los grupos seleccionados (filtro) para una lista."""
    ul = await get_list(list_id, device_id, db)
    if not ul:
        return False
    ul.selected_groups = json.dumps(groups, ensure_ascii=False)
    await db.commit()
    return True


# ── Lista activa ──────────────────────────────────────────────────────────────

async def set_active_list(list_id: str, device_id: str, db: AsyncSession) -> bool:
    """Marca una lista como activa y desactiva el resto del mismo dispositivo."""
    # Desactivar todas
    all_lists = await get_user_lists(device_id, db)
    for ul in all_lists:
        ul.is_active = ul.id == list_id
    await db.commit()
    return True
