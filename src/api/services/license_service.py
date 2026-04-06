"""
Gestión de licencias: trial gratuito 7 días, suscripción de pago, códigos de activación.
"""
import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.activation_code import ActivationCode
from src.api.models.app_user import AppUser

TRIAL_DAYS = 7
SUBSCRIPTION_DAYS = 365  # 1 año = 3 €


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Usuario ───────────────────────────────────────────────────────────────────

async def get_or_create_user(db: AsyncSession, device_id: str) -> AppUser:
    """Devuelve el usuario existente o crea uno nuevo (inicia el trial)."""
    result = await db.execute(select(AppUser).where(AppUser.device_id == device_id))
    user = result.scalar_one_or_none()
    if not user:
        user = AppUser(device_id=device_id, trial_start=_now())
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def check_license(device_id: str, db: AsyncSession) -> dict:
    """
    Comprueba el estado de la licencia de un dispositivo.

    Returns::
        {
          "status": "trial" | "active" | "expired",
          "type": "trial" | "subscription" | "expired",
          "expires": "ISO-8601",
          "days_left": int   # solo en trial
        }
    """
    user = await get_or_create_user(db, device_id)
    now = _now()

    trial_end = user.trial_start + timedelta(days=TRIAL_DAYS)

    # ── Suscripción de pago activa ─────────────────────────────────────────────
    if user.subscription_end and user.subscription_end > now:
        days_left = (user.subscription_end - now).days
        return {
            "status": "active",
            "type": "subscription",
            "expires": user.subscription_end.isoformat(),
            "days_left": days_left,
        }

    # ── Periodo de prueba ─────────────────────────────────────────────────────
    if now <= trial_end:
        days_left = (trial_end - now).days
        return {
            "status": "trial",
            "type": "trial",
            "expires": trial_end.isoformat(),
            "days_left": days_left,
        }

    # ── Expirado ──────────────────────────────────────────────────────────────
    return {
        "status": "expired",
        "type": "expired",
        "expires": trial_end.isoformat(),
        "days_left": 0,
    }


# ── Códigos de activación ─────────────────────────────────────────────────────

def _generate_code() -> str:
    """Genera un código tipo XXXX-XXXX-XXXX."""
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return "-".join(parts)


async def create_activation_code(
    db: AsyncSession,
    duration_days: int = SUBSCRIPTION_DAYS,
    note: str | None = None,
) -> ActivationCode:
    """Crea un nuevo código de activación sin usar."""
    # Evitar colisiones (muy improbable pero seguro)
    for _ in range(10):
        code = _generate_code()
        existing = await db.execute(select(ActivationCode).where(ActivationCode.code == code))
        if not existing.scalar_one_or_none():
            break

    ac = ActivationCode(code=code, duration_days=duration_days, note=note)
    db.add(ac)
    await db.commit()
    await db.refresh(ac)
    return ac


async def activate_with_code(device_id: str, code: str, db: AsyncSession) -> dict:
    """
    Activa una suscripción usando un código.

    Returns::
        {"success": True, "expires": "ISO-8601"} | {"success": False, "error": "..."}
    """
    result = await db.execute(
        select(ActivationCode).where(ActivationCode.code == code.upper().strip())
    )
    ac = result.scalar_one_or_none()

    if not ac:
        return {"success": False, "error": "Código inválido"}
    if ac.used_by_device:
        return {"success": False, "error": "Este código ya ha sido utilizado"}

    user = await get_or_create_user(db, device_id)
    now = _now()

    # Acumular sobre la suscripción existente (si aún está vigente)
    base = user.subscription_end if user.subscription_end and user.subscription_end > now else now
    new_end = base + timedelta(days=ac.duration_days)

    user.subscription_end = new_end
    ac.used_by_device = device_id
    ac.used_at = now
    await db.commit()

    return {"success": True, "expires": new_end.isoformat()}


async def gift_subscription(
    device_id: str, duration_days: int, db: AsyncSession
) -> dict:
    """Admin: regala días de suscripción a un dispositivo."""
    user = await get_or_create_user(db, device_id)
    now = _now()
    base = user.subscription_end if user.subscription_end and user.subscription_end > now else now
    new_end = base + timedelta(days=duration_days)
    user.subscription_end = new_end
    await db.commit()
    return {"success": True, "device_id": device_id, "expires": new_end.isoformat()}
