#!/usr/bin/env python3
"""
Crea o actualiza un usuario administrador en Cine Tv Portal.

Uso:
    python scripts/create_admin.py <usuario> <contraseña>

Ejemplo:
    python scripts/create_admin.py admin miContraseñaSegura
"""
import asyncio
import sys
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.models.admin_user import AdminUser
from src.core.database import create_tables, engine


def _hash(password: str) -> str:
    """Hash bcrypt compatible con passlib y con bcrypt>=4 directamente."""
    try:
        # Intentar con passlib primero (compatible con la API en ejecución)
        from passlib.context import CryptContext
        return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)
    except Exception:
        # Fallback: usar bcrypt directamente
        import bcrypt as _bcrypt
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


async def create_admin(username: str, password: str) -> None:
    # Crear tablas si no existen
    await create_tables()

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        existing = (
            await db.execute(select(AdminUser).where(AdminUser.username == username))
        ).scalar_one_or_none()

        hashed = _hash(password)
        if existing:
            existing.hashed_password = hashed
            await db.commit()
            print(f"✅ Contraseña de '{username}' actualizada correctamente.")
        else:
            admin = AdminUser(username=username, hashed_password=hashed)
            db.add(admin)
            await db.commit()
            print(f"✅ Admin '{username}' creado correctamente.")
            print(f"   Accede en: http://<tu-ip>:8000/portal")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))
