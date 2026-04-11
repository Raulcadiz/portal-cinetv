"""Pydantic schemas for content (movies, series, live) endpoints."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class Contenido(BaseModel):
    """Representa un contenido (película, serie, o canal en vivo)."""
    id: int = 0
    title: str
    type: str = "live"
    stream_url: str = ""
    image: Optional[str] = None
    group_title: Optional[str] = None
    added_at: Optional[str] = None
    year: Optional[int] = None
    genres: Optional[list[str]] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    server: Optional[str] = None
    live_urls: Optional[list[str]] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class SerieAgrupada(BaseModel):
    """Serie agrupada por título (múltiples temporadas)."""
    id: int = 0
    title: str
    image: Optional[str] = None
    genres: Optional[list[str]] = None
    seasons: int = 0
    season_count: int = 0
    episode_count: int = 0
    year: Optional[int] = None

    model_config = {"from_attributes": True}


class PagedResponse(BaseModel):
    """Respuesta paginada genérica."""
    total: int = 0
    page: int = 1
    pages: int = 1
    items: list[Any] = []
