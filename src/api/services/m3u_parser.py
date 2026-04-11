"""
Utilidades para parsear contenido M3U/M3U8 y extraer grupos de canales.
"""
import re
from typing import List

import httpx


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
