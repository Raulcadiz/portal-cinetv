"""
Servicio para obtener contenido (películas, series, canales en vivo) desde las listas IPTV del usuario.
"""
import re
from collections import defaultdict
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.user_list import UserList
from src.api.services.license_service import check_license
from src.api.services.m3u_parser import (
    M3uChannel,
    build_xtream_m3u_url,
    fetch_url_content,
    get_live_channels,
    get_movie_channels,
    get_series_channels,
    parse_channels,
)


async def _get_list_content(list_id: str, device_id: str, db: AsyncSession) -> Optional[str]:
    """Obtiene el contenido M3U de una lista, descargando si es necesario."""
    from src.api.services import user_list_service
    ul = await user_list_service.get_list(list_id, device_id, db)
    if not ul:
        return None
    
    return await _fetch_m3u_content(ul)


async def _fetch_m3u_content(ul: UserList) -> Optional[str]:
    """Descarga o retorna el contenido M3U según el tipo de lista."""
    try:
        if ul.list_type == "file" and ul.content:
            return ul.content
        elif ul.list_type == "url" and ul.url:
            return await fetch_url_content(ul.url)
        elif ul.list_type == "xtream":
            m3u_url = build_xtream_m3u_url(ul.xtream_server, ul.xtream_user, ul.xtream_pass)
            return await fetch_url_content(m3u_url)
    except Exception:
        pass
    return None


async def get_all_lists_content(device_id: str, db: AsyncSession) -> Optional[str]:
    """Obtiene contenido combinado de todas las listas activas del usuario."""
    from src.api.services import user_list_service
    lists = await user_list_service.get_user_lists(device_id, db)
    
    active_lists = [l for l in lists if l.is_active] or lists
    contents = []
    
    for ul in active_lists:
        content = await _fetch_m3u_content(ul)
        if content:
            contents.append(content)
    
    return "\n".join(contents) if contents else None


def _parse_year_from_title(title: str) -> Optional[int]:
    """Extrae el año del título si está presente, ej: 'Movie Title (2023)'."""
    match = re.search(r'\((\d{4})\)', title)
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2100:
            return year
    return None


def _clean_title(title: str) -> str:
    """Limpia el título removiendo el año entre paréntesis."""
    return re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()


def _extract_season_episode(title: str) -> Tuple[Optional[int], Optional[int]]:
    """Extrae temporada y episodio del título, ej: 'S01E05' o '1x05'."""
    match_sxe = re.search(r'[Ss](\d+)[Ee](\d+)', title)
    if match_sxe:
        return int(match_sxe.group(1)), int(match_sxe.group(2))
    
    match_1x = re.search(r'(\d+)x(\d+)', title)
    if match_1x:
        return int(match_1x.group(1)), int(match_1x.group(2))
    
    return None, None


def _channel_to_content(ch: M3uChannel, index: int, content_type: str = "live") -> dict:
    """Convierte un M3uChannel a dict de Contenido."""
    year = _parse_year_from_title(ch.title)
    clean_title = _clean_title(ch.title)
    season, episode = _extract_season_episode(ch.title)
    
    return {
        "id": index,
        "title": clean_title,
        "type": content_type,
        "stream_url": ch.url,
        "image": ch.logo,
        "group_title": ch.group,
        "year": year,
        "season": season,
        "episode": episode,
        "genres": [ch.group] if ch.group else None,
    }


def _paginate(items: List[dict], page: int, limit: int) -> Tuple[List[dict], int, int]:
    """Paglina una lista y devuelve (items_paginados, total, total_pages)."""
    total = len(items)
    total_pages = max(1, (total + limit - 1) // limit)
    start = (page - 1) * limit
    end = start + limit
    return items[start:end], total, total_pages


async def get_movies(
    device_id: str,
    db: AsyncSession,
    page: int = 1,
    limit: int = 24,
    query: Optional[str] = None,
    genero: Optional[str] = None,
    sort: Optional[str] = None,
) -> Tuple[List[dict], int, int]:
    """Obtiene películas paginadas de las listas del usuario."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return [], 0, 1
    
    channels = get_movie_channels(content)
    
    items = [_channel_to_content(ch, i, "movie") for i, ch in enumerate(channels)]
    
    if query:
        query_lower = query.lower()
        items = [item for item in items if query_lower in item["title"].lower()]
    
    if genero:
        items = [item for item in items if item.get("group_title", "").lower() == genero.lower()]
    
    if sort == "year":
        items.sort(key=lambda x: (x.get("year") or 0, x["title"]))
    elif sort == "title":
        items.sort(key=lambda x: x["title"])
    else:
        items.sort(key=lambda x: x["title"])
    
    return _paginate(items, page, limit)


async def get_series(
    device_id: str,
    db: AsyncSession,
    page: int = 1,
    limit: int = 24,
    query: Optional[str] = None,
    genero: Optional[str] = None,
    sort: Optional[str] = None,
) -> Tuple[List[dict], int, int]:
    """Obtiene series agrupadas paginadas de las listas del usuario."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return [], 0, 1
    
    channels = get_series_channels(content)
    
    episodes = [_channel_to_content(ch, i, "series") for i, ch in enumerate(channels)]
    
    grouped = defaultdict(lambda: {"episodes": 0, "seasons": set(), "first_item": None})
    
    for ep in episodes:
        title = ep["title"]
        if ep["season"]:
            grouped[title]["seasons"].add(ep["season"])
        grouped[title]["episodes"] += 1
        if grouped[title]["first_item"] is None:
            grouped[title]["first_item"] = ep
    
    series_list = []
    for title, data in grouped.items():
        first = data["first_item"]
        seasons = len(data["seasons"]) if data["seasons"] else 1
        year = first.get("year") if first else None
        image = first.get("image") if first else None
        genre = first.get("group_title") if first else None
        
        series_list.append({
            "id": hash(title) % 1000000,
            "title": title,
            "image": image,
            "genres": [genre] if genre else None,
            "seasons": seasons,
            "season_count": seasons,
            "episode_count": data["episodes"],
            "year": year,
        })
    
    if query:
        query_lower = query.lower()
        series_list = [s for s in series_list if query_lower in s["title"].lower()]
    
    if genero:
        series_list = [s for s in series_list 
                      if s.get("genres") and genero.lower() in [g.lower() for g in s["genres"]]]
    
    if sort == "year":
        series_list.sort(key=lambda x: (x.get("year") or 0, x["title"]))
    elif sort == "title":
        series_list.sort(key=lambda x: x["title"])
    else:
        series_list.sort(key=lambda x: x["title"])
    
    return _paginate(series_list, page, limit)


async def get_serie_episodes(
    titulo: str,
    device_id: str,
    db: AsyncSession,
) -> List[dict]:
    """Obtiene todos los episodios de una serie específica."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return []
    
    channels = get_series_channels(content)
    clean_search = _clean_title(titulo).lower()
    
    episodes = []
    for i, ch in enumerate(channels):
        if clean_search in _clean_title(ch.title).lower():
            ep = _channel_to_content(ch, i, "series")
            ep["id"] = i
            episodes.append(ep)
    
    episodes.sort(key=lambda x: (x.get("season") or 0, x.get("episode") or 0, x["title"]))
    
    for idx, ep in enumerate(episodes):
        ep["id"] = idx + 1
    
    return episodes


async def get_live(
    device_id: str,
    db: AsyncSession,
    page: int = 1,
    limit: int = 100,
) -> Tuple[List[dict], int, int]:
    """Obtiene canales en vivo paginados de las listas del usuario."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return [], 0, 1
    
    channels = get_live_channels(content)
    items = [_channel_to_content(ch, i, "live") for i, ch in enumerate(channels)]
    
    return _paginate(items, page, limit)


async def get_trending(
    device_id: str,
    db: AsyncSession,
    limit: int = 30,
) -> List[dict]:
    """Obtiene contenido trending (mezcla de películas y series recientes)."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return []
    
    all_channels = parse_channels(content)
    
    items = []
    for i, ch in enumerate(all_channels):
        if "/movie/" in ch.url.lower() or "/series/" in ch.url.lower():
            ctype = "movie" if "/movie/" in ch.url.lower() else "series"
            items.append(_channel_to_content(ch, i, ctype))
    
    items.sort(key=lambda x: x["title"])
    
    return items[:limit]


async def get_contenido_by_id(
    content_id: int,
    device_id: str,
    db: AsyncSession,
) -> Optional[dict]:
    """Obtiene un contenido específico por ID."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return None
    
    all_channels = parse_channels(content)
    
    if 0 <= content_id < len(all_channels):
        ch = all_channels[content_id]
        ctype = "movie" if _is_movie(ch) else "series" if _is_series(ch) else "live"
        return _channel_to_content(ch, content_id, ctype)
    
    return None


def _is_movie(ch: M3uChannel) -> bool:
    group_lower = ch.group.lower()
    url_lower = ch.url.lower()
    movie_kw = {"pelicula", "peliculas", "peli", "pelis", "movie", "movies", "film", "films"}
    return any(k in group_lower for k in movie_kw) or "/movie/" in url_lower


def _is_series(ch: M3uChannel) -> bool:
    group_lower = ch.group.lower()
    url_lower = ch.url.lower()
    series_kw = {"serie", "series", "temporada", "miniserie", "miniseries"}
    return any(k in group_lower for k in series_kw) or "/series/" in url_lower


async def get_generos(device_id: str, db: AsyncSession) -> List[str]:
    """Obtiene la lista de géneros/grupos disponibles."""
    content = await get_all_lists_content(device_id, db)
    if not content:
        return []
    
    channels = parse_channels(content)
    groups = {ch.group for ch in channels if ch.group}
    
    return sorted(groups)
