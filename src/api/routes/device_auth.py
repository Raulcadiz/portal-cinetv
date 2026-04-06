"""
Rutas de autenticación/licencia para la app Android.
No requieren JWT — se identifican por device_id.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import license_service
from src.core.database import get_db

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    device_id: str


class ActivateRequest(BaseModel):
    device_id: str
    code: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    summary="Registra un dispositivo e inicia el trial de 7 días",
)
async def register_device(
    body: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Primera llamada de la app.
    Si el device_id ya existe devuelve su estado sin modificarlo.
    """
    if not body.device_id or len(body.device_id) < 8:
        raise HTTPException(status_code=422, detail="device_id inválido")

    license_info = await license_service.check_license(body.device_id, db)
    return {"device_id": body.device_id, **license_info}


@router.get(
    "/license",
    summary="Consulta el estado de licencia de un dispositivo",
)
async def get_license(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not device_id or len(device_id) < 8:
        raise HTTPException(status_code=422, detail="device_id inválido")

    return await license_service.check_license(device_id, db)


@router.post(
    "/activate",
    summary="Activa una suscripción usando un código",
)
async def activate_code(
    body: ActivateRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.device_id or not body.code:
        raise HTTPException(status_code=422, detail="Faltan parámetros")

    result = await license_service.activate_with_code(body.device_id, body.code, db)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
