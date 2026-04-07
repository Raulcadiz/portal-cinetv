"""
Gestión de listas IPTV desde la app Android.
Se identifican por device_id — sin JWT (la licencia es el control de acceso).
"""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import license_service, user_list_service
from src.core.config import settings
from src.core.database import get_db

router = APIRouter()

_EXTM3U_HEADER = b"#EXTM3U"


# ── Schemas ───────────────────────────────────────────────────────────────────

class AddUrlListRequest(BaseModel):
    device_id: str
    name: str = ""
    url: str


class AddXtreamListRequest(BaseModel):
    device_id: str
    name: str = ""
    server: str
    username: str
    password: str


class SetActiveRequest(BaseModel):
    device_id: str


class SetGroupsRequest(BaseModel):
    device_id: str
    groups: list[str]


# ── Helper ────────────────────────────────────────────────────────────────────

async def _require_license(device_id: str, db: AsyncSession):
    """Lanza 403 si la licencia está expirada."""
    info = await license_service.check_license(device_id, db)
    if info["status"] == "expired":
        raise HTTPException(
            status_code=403,
            detail="Licencia expirada. Renueva tu suscripción en cinetv.app",
        )


def _serialize_list(ul) -> dict:
    return {
        "id": ul.id,
        "name": ul.name,
        "list_type": ul.list_type,
        "url": ul.url,
        "xtream_server": ul.xtream_server,
        "xtream_user": ul.xtream_user,
        # No devolvemos la contraseña de Xtream
        "selected_groups": json.loads(ul.selected_groups) if ul.selected_groups else None,
        "is_active": ul.is_active,
        "created_at": ul.created_at.isoformat() if ul.created_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="Obtiene las listas del dispositivo",
)
async def get_lists(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _require_license(device_id, db)
    lists = await user_list_service.get_user_lists(device_id, db)
    return [_serialize_list(ul) for ul in lists]


@router.post(
    "/url",
    status_code=201,
    summary="Añade una lista por URL",
)
async def add_url(
    body: AddUrlListRequest,
    db: AsyncSession = Depends(get_db),
):
    await _require_license(body.device_id, db)
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL inválida")
    ul = await user_list_service.add_url_list(body.device_id, body.name, body.url, db)
    return _serialize_list(ul)


@router.post(
    "/xtream",
    status_code=201,
    summary="Añade una lista Xtream Codes",
)
async def add_xtream(
    body: AddXtreamListRequest,
    db: AsyncSession = Depends(get_db),
):
    await _require_license(body.device_id, db)
    ul = await user_list_service.add_xtream_list(
        body.device_id, body.name, body.server, body.username, body.password, db
    )
    return _serialize_list(ul)


@router.post(
    "/file",
    status_code=201,
    summary="Sube un archivo M3U",
)
async def upload_file(
    device_id: str = Form(...),
    name: str = Form(default=""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await _require_license(device_id, db)

    raw = await file.read(settings.max_m3u8_size_bytes + 1)
    if len(raw) > settings.max_m3u8_size_bytes:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande")
    if not raw.lstrip().startswith(_EXTM3U_HEADER):
        raise HTTPException(status_code=400, detail="No es un archivo M3U válido")

    content = raw.decode("utf-8", errors="replace")
    ul = await user_list_service.add_file_list(device_id, name, content, db)
    return _serialize_list(ul)


@router.delete(
    "/{list_id}",
    summary="Elimina una lista",
)
async def delete_list(
    list_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    deleted = await user_list_service.delete_list(list_id, device_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    return {"deleted": True}


@router.get(
    "/{list_id}/groups",
    summary="Devuelve los grupos disponibles en una lista",
)
async def get_groups(
    list_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _require_license(device_id, db)
    groups = await user_list_service.get_list_groups(list_id, device_id, db)
    return {"groups": groups}


@router.post(
    "/{list_id}/groups",
    summary="Guarda los grupos seleccionados (filtro)",
)
async def set_groups(
    list_id: str,
    body: SetGroupsRequest,
    db: AsyncSession = Depends(get_db),
):
    ok = await user_list_service.set_selected_groups(
        list_id, body.device_id, body.groups, db
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    return {"saved": True}


@router.post(
    "/{list_id}/activate",
    summary="Establece esta lista como la activa",
)
async def set_active(
    list_id: str,
    body: SetActiveRequest,
    db: AsyncSession = Depends(get_db),
):
    ok = await user_list_service.set_active_list(list_id, body.device_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    return {"activated": True}


@router.get(
    "/{list_id}/m3u",
    summary="Proxy del contenido M3U con credenciales almacenadas",
)
async def get_list_m3u(
    list_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve el contenido M3U de la lista usando las credenciales almacenadas
    en el servidor (sin exponerlas al cliente). Usado por la app Android.
    """
    import httpx
    from fastapi.responses import Response

    from src.api.services.m3u_parser import build_xtream_m3u_url, fetch_url_content

    await _require_license(device_id, db)
    ul = await user_list_service.get_list(list_id, device_id, db)
    if not ul:
        raise HTTPException(status_code=404, detail="Lista no encontrada")

    # Lista subida como archivo — devolver contenido almacenado
    if ul.list_type == "file":
        return Response(
            content=(ul.content or "").encode("utf-8"),
            media_type="text/plain; charset=utf-8",
        )

    # Lista por URL directa — streaming proxy (no espera a descargar todo)
    if ul.list_type == "url" and ul.url:
        from fastapi.responses import StreamingResponse

        async def _stream_url():
            try:
                async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                    async with client.stream("GET", ul.url) as r:
                        r.raise_for_status()
                        async for chunk in r.aiter_bytes(chunk_size=65536):
                            yield chunk
            except Exception:
                pass

        return StreamingResponse(_stream_url(), media_type="text/plain; charset=utf-8")

    # Lista Xtream Codes — construir URL con credenciales y hacer streaming proxy
    if ul.list_type == "xtream":
        from fastapi.responses import StreamingResponse

        m3u_url = build_xtream_m3u_url(ul.xtream_server, ul.xtream_user, ul.xtream_pass)

        async def _stream_xtream():
            try:
                async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                    async with client.stream("GET", m3u_url) as r:
                        r.raise_for_status()
                        async for chunk in r.aiter_bytes(chunk_size=65536):
                            yield chunk
            except Exception:
                pass

        return StreamingResponse(_stream_xtream(), media_type="text/plain; charset=utf-8")

    raise HTTPException(status_code=400, detail="Tipo de lista no soportado")
