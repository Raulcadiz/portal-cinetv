"""
Utilidades para parsear contenido M3U/M3U8 y extraer grupos de canales.
"""
import re
from dataclasses import dataclass
from typing import List, Optional

import httpx


@dataclass
class M3uChannel:
    """Representa un canal individual parseado de M3U."""
    title: str
    url: str
    group: str = ""
    logo: Optional[str] = None
    tvg_id: Optional[str] = None
    tvg_name: Optional[str] = None
    

MOVIE_KEYWORDS = frozenset({
    "pelicula", "peliculas", "peli", "pelis",
    "movie", "movies", "film", "films",
    "cinema", "cine",
})

SERIES_KEYWORDS = frozenset({
    "serie", "series", "temporada",
    "miniserie", "miniseries",
    "docuserie", "docuseries",
    "docu-serie", "docu-series",
})


def _is_movie_channel(channel: M3uChannel) -> bool:
    """Detecta si un canal es una película basándose en group o URL."""
    group_lower = channel.group.lower()
    url_lower = channel.url.lower()
    
    if any(kw in group_lower for kw in MOVIE_KEYWORDS):
        return True
    if "/movie/" in url_lower or "/movies/" in url_lower:
        return True
    return False


def _is_series_channel(channel: M3uChannel) -> bool:
    """Detecta si un canal es una serie basándose en group o URL."""
    group_lower = channel.group.lower()
    url_lower = channel.url.lower()
    
    if any(kw in group_lower for kw in SERIES_KEYWORDS):
        return True
    if "/series/" in url_lower or "/seasons/" in url_lower:
        return True
    return False


def _parse_extinf(line: str) -> dict:
    """Extrae atributos de una línea #EXTINF."""
    attrs = {}
    
    match_id = re.search(r'tvg-id="([^"]*)"', line)
    if match_id:
        attrs["tvg_id"] = match_id.group(1)
    
    match_name = re.search(r'tvg-name="([^"]*)"', line)
    if match_name:
        attrs["tvg_name"] = match_name.group(1)
    
    match_logo = re.search(r'tvg-logo="([^"]*)"', line)
    if match_logo:
        attrs["logo"] = match_logo.group(1)
    
    match_group = re.search(r'group-title="([^"]*)"', line)
    if match_group:
        attrs["group"] = match_group.group(1)
    
    title_match = re.search(r',(.+)$', line)
    if title_match:
        attrs["title"] = title_match.group(1).strip()
    
    return attrs


def parse_channels(content: str) -> List[M3uChannel]:
    """Parsea el contenido M3U y devuelve una lista de canales."""
    channels: List[M3uChannel] = []
    lines = content.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("#EXTINF:"):
            attrs = _parse_extinf(line)
            title = attrs.get("title", "Unknown")
            group = attrs.get("group", "")
            logo = attrs.get("logo")
            tvg_id = attrs.get("tvg_id")
            tvg_name = attrs.get("tvg_name")
            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith("#"):
                    channel = M3uChannel(
                        title=title,
                        url=next_line,
                        group=group,
                        logo=logo,
                        tvg_id=tvg_id,
                        tvg_name=tvg_name,
                    )
                    channels.append(channel)
                    i += 2
                    continue
        
        i += 1
    
    return channels


def get_movie_channels(content: str) -> List[M3uChannel]:
    """Devuelve solo los canales que son películas."""
    return [ch for ch in parse_channels(content) if _is_movie_channel(ch)]


def get_series_channels(content: str) -> List[M3uChannel]:
    """Devuelve solo los canales que son series."""
    return [ch for ch in parse_channels(content) if _is_series_channel(ch)]


def get_live_channels(content: str) -> List[M3uChannel]:
    """Devuelve solo los canales que son en vivo (no películas ni series)."""
    all_channels = parse_channels(content)
    return [ch for ch in all_channels 
            if not _is_movie_channel(ch) and not _is_series_channel(ch)]


async def fetch_url_content(url: str, timeout: int = 30) -> str:
    """Descarga el contenido de una URL como texto."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def parse_groups(content: str) -> List[str]:
    """
    Extrae los grupos únicos de un M3U a partir del atributo group-title.
    Devuelve lista ordenada sin duplicados.
    """
    groups: set[str] = set()
    for line in content.splitlines():
        if line.startswith("#EXTINF"):
            match = re.search(r'group-title="([^"]*)"', line)
            if match:
                group = match.group(1).strip()
                if group:
                    groups.add(group)
    return sorted(groups)


def build_xtream_m3u_url(server: str, username: str, password: str) -> str:
    """Construye la URL M3U de una cuenta Xtream Codes."""
    server = server.rstrip("/")
    return f"{server}/get.php?username={username}&password={password}&type=m3u_plus&output=ts"
