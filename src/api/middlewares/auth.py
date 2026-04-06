"""JWT Bearer authentication for the admin portal API."""
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt_lib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.admin_user import AdminUser
from src.core.config import settings
from src.core.database import get_db

_bearer = HTTPBearer(auto_error=True)


# ── Password helpers (bcrypt directo, sin passlib) ────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _bcrypt_lib.hashpw(plain.encode("utf-8"), _bcrypt_lib.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches *hashed*."""
    try:
        return _bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(subject: str) -> str:
    """
    Create a signed JWT for *subject* (admin username).
    Expiry is controlled by ``settings.jwt_ttl_hours``.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_ttl_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> str:
    """
    Decode and validate a JWT.  Returns the ``sub`` claim.
    Raises :class:`HTTPException` 401 on any error.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """
    FastAPI dependency — verifies the Bearer JWT and returns the admin user.
    Inject with ``Depends(get_current_admin)`` on any protected endpoint.
    """
    username = _decode_token(credentials.credentials)
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
