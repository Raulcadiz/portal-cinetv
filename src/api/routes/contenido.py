"""
Rutas del portal para obtener contenido (películas, series, canales en vivo).
Todas requieren licencia válida del dispositivo.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.contenido import Contenido, PagedResponse, SerieAgrupada
from src.api.services import contenido_service, license_service
from src.core.database import get_db

router = APIRouter()


async def _require_license(device_id: str, db: AsyncSession):
    """Verifica que la licencia del dispositivo sea válida."""
    info = await license_service.check_license(device_id, db)
    if info["status"] == "expired":
        raise HTTPException(
            status_code=403,
            detail="Licencia expirada. Renueva tu suscripción.",
        )


@router.get(
    "/trending",
    response_model=list[Contenido],
    summary="Contenido trending",
)
async def get_trending(
    limit: int = Query(default=30, ge=1, le=100),
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve contenido trending (películas y series recientes)."""
    await _require_license(device_id, db)
    items = await contenido_service.get_trending(device_id, db, limit)
    return items


@router.get(
    "/peliculas",
    response_model=PagedResponse,
    summary="Lista de películas",
)
async def get_peliculas(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    q: Optional[str] = Query(default=None),
    genero: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve lista paginada de películas."""
    await _require_license(device_id, db)
    items, total, pages = await contenido_service.get_movies(
        device_id, db, page, limit, q, genero, sort
    )
    return PagedResponse(total=total, page=page, pages=pages, items=items)


@router.get(
    "/series",
    response_model=PagedResponse,
    summary="Lista de series",
)
async def get_series(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    q: Optional[str] = Query(default=None),
    genero: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve lista paginada de series agrupadas."""
    await _require_license(device_id, db)
    items, total, pages = await contenido_service.get_series(
        device_id, db, page, limit, q, genero, sort
    )
    return PagedResponse(total=total, page=page, pages=pages, items=items)


@router.get(
    "/live",
    response_model=PagedResponse,
    summary="Canales en vivo",
)
async def get_live(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve lista paginada de canales en vivo."""
    await _require_license(device_id, db)
    items, total, pages = await contenido_service.get_live(device_id, db, page, limit)
    return PagedResponse(total=total, page=page, pages=pages, items=items)


@router.get(
    "/live/curados",
    response_model=list[Contenido],
    summary="Canales curados",
)
async def get_canales_curados(
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve canales curados por el administrador."""
    await _require_license(device_id, db)
    items, _, _ = await contenido_service.get_live(device_id, db, page=1, limit=50)
    return items[:20]


@router.get(
    "/series/{titulo}/episodios",
    response_model=list[Contenido],
    summary="Episodios de una serie",
)
async def get_serie_episodios(
    titulo: str,
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve todos los episodios de una serie específica."""
    await _require_license(device_id, db)
    episodes = await contenido_service.get_serie_episodes(titulo, device_id, db)
    return episodes


@router.get(
    "/contenido/{content_id}",
    response_model=Contenido,
    summary="Detalle de contenido",
)
async def get_contenido(
    content_id: int,
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve el detalle de un contenido específico."""
    await _require_license(device_id, db)
    contenido = await contenido_service.get_contenido_by_id(content_id, device_id, db)
    if not contenido:
        raise HTTPException(status_code=404, detail="Contenido no encontrado")
    return contenido


@router.get(
    "/generos",
    response_model=list[str],
    summary="Lista de géneros",
)
async def get_generos(
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve la lista de géneros/grupos disponibles."""
    await _require_license(device_id, db)
    return await contenido_service.get_generos(device_id, db)
