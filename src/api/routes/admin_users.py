"""
Panel de administración: gestión de usuarios, códigos de activación y regalos.
Requiere JWT de administrador.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middlewares.auth import get_current_admin
from src.api.models.activation_code import ActivationCode
from src.api.models.admin_user import AdminUser
from src.api.models.app_user import AppUser
from src.api.services import license_service
from src.core.database import get_db

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateCodeRequest(BaseModel):
    duration_days: int = 365
    quantity: int = 1
    note: str | None = None


class GiftRequest(BaseModel):
    device_id: str
    duration_days: int = 365


class PushListRequest(BaseModel):
    url: str
    name: str = ""
    set_active: bool = True


# ── Usuarios ──────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    summary="Lista todos los usuarios registrados",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    """Devuelve usuarios paginados con su estado de licencia."""
    from src.api.services.license_service import check_license

    offset = (page - 1) * limit
    result = await db.execute(
        select(AppUser).order_by(AppUser.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()

    count_result = await db.execute(select(func.count()).select_from(AppUser))
    total = count_result.scalar_one()

    items = []
    for u in users:
        lic = await check_license(u.device_id, db)
        items.append(
            {
                "device_id": u.device_id,
                "trial_start": u.trial_start.isoformat() if u.trial_start else None,
                "subscription_end": (
                    u.subscription_end.isoformat() if u.subscription_end else None
                ),
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "license": lic,
            }
        )

    return {"total": total, "page": page, "pages": -(-total // limit), "items": items}


@router.get(
    "/users/{device_id}",
    summary="Detalle de un usuario",
)
async def get_user(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(select(AppUser).where(AppUser.device_id == device_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    lic = await license_service.check_license(device_id, db)
    return {
        "device_id": user.device_id,
        "trial_start": user.trial_start.isoformat() if user.trial_start else None,
        "subscription_end": (
            user.subscription_end.isoformat() if user.subscription_end else None
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "license": lic,
    }


# ── Estadísticas ──────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Estadísticas globales",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    from datetime import datetime, timezone
    from src.api.models.user_list import UserList

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    total_users = (
        await db.execute(select(func.count()).select_from(AppUser))
    ).scalar_one()

    active_subs = (
        await db.execute(
            select(func.count())
            .select_from(AppUser)
            .where(AppUser.subscription_end > now)
        )
    ).scalar_one()

    total_codes = (
        await db.execute(select(func.count()).select_from(ActivationCode))
    ).scalar_one()

    used_codes = (
        await db.execute(
            select(func.count())
            .select_from(ActivationCode)
            .where(ActivationCode.used_by_device.isnot(None))
        )
    ).scalar_one()

    total_lists = (
        await db.execute(select(func.count()).select_from(UserList))
    ).scalar_one()

    return {
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_codes": total_codes,
        "used_codes": used_codes,
        "available_codes": total_codes - used_codes,
        "total_lists": total_lists,
    }


# ── Códigos de activación ─────────────────────────────────────────────────────

@router.post(
    "/codes",
    status_code=201,
    summary="Genera uno o varios códigos de activación",
)
async def create_codes(
    body: CreateCodeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    if body.quantity < 1 or body.quantity > 100:
        raise HTTPException(status_code=422, detail="quantity debe estar entre 1 y 100")

    codes = []
    for _ in range(body.quantity):
        ac = await license_service.create_activation_code(
            db, duration_days=body.duration_days, note=body.note
        )
        codes.append(
            {
                "code": ac.code,
                "duration_days": ac.duration_days,
                "note": ac.note,
                "created_at": ac.created_at.isoformat() if ac.created_at else None,
            }
        )
    return {"codes": codes}


@router.get(
    "/codes",
    summary="Lista todos los códigos de activación",
)
async def list_codes(
    used: bool | None = Query(default=None, description="Filtrar: True=usados, False=disponibles"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    q = select(ActivationCode).order_by(ActivationCode.created_at.desc())
    if used is True:
        q = q.where(ActivationCode.used_by_device.isnot(None))
    elif used is False:
        q = q.where(ActivationCode.used_by_device.is_(None))

    offset = (page - 1) * limit
    result = await db.execute(q.offset(offset).limit(limit))
    codes = result.scalars().all()

    count_q = select(func.count()).select_from(ActivationCode)
    if used is True:
        count_q = count_q.where(ActivationCode.used_by_device.isnot(None))
    elif used is False:
        count_q = count_q.where(ActivationCode.used_by_device.is_(None))
    total = (await db.execute(count_q)).scalar_one()

    return {
        "total": total,
        "page": page,
        "items": [
            {
                "code": c.code,
                "duration_days": c.duration_days,
                "note": c.note,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "used_by_device": c.used_by_device,
                "used_at": c.used_at.isoformat() if c.used_at else None,
            }
            for c in codes
        ],
    }


# ── Asignar lista a dispositivo ───────────────────────────────────────────────

@router.post(
    "/users/{device_id}/push-list",
    summary="Asigna una lista M3U a un dispositivo (aparece en la app)",
)
async def push_list_to_device(
    device_id: str,
    body: PushListRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Crea una entrada UserList para el dispositivo indicado.
    La lista aparece inmediatamente en «Mis listas» de la app.
    Si ``set_active=True`` (por defecto), se marca como lista activa.
    """
    from src.api.services import user_list_service

    result = await db.execute(select(AppUser).where(AppUser.device_id == device_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    ul = await user_list_service.add_url_list(
        device_id, body.name or "Lista asignada por admin", body.url, db
    )
    if body.set_active:
        await user_list_service.set_active_list(ul.id, device_id, db)

    return {
        "id": ul.id,
        "device_id": device_id,
        "url": body.url,
        "active": body.set_active,
        "message": "Lista asignada correctamente",
    }


# ── Lista de listas de un dispositivo ─────────────────────────────────────────

@router.get(
    "/users/{device_id}/lists",
    summary="Listas IPTV de un dispositivo",
)
async def get_device_lists(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    """Devuelve las listas IPTV configuradas para un dispositivo."""
    from src.api.services import user_list_service

    lists = await user_list_service.get_user_lists(device_id, db)
    return [
        {
            "id": ul.id,
            "name": ul.name,
            "list_type": ul.list_type,
            "url": ul.url,
            "xtream_server": ul.xtream_server,
            "is_active": ul.is_active,
            "created_at": ul.created_at.isoformat() if ul.created_at else None,
        }
        for ul in lists
    ]


# ── Regalo de suscripción ─────────────────────────────────────────────────────

@router.post(
    "/gift",
    summary="Regala días de suscripción a un dispositivo",
)
async def gift_subscription(
    body: GiftRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    if body.duration_days < 1:
        raise HTTPException(status_code=422, detail="duration_days debe ser >= 1")

    result = await license_service.gift_subscription(body.device_id, body.duration_days, db)
    return result
