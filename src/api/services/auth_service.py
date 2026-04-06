"""Admin authentication service."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middlewares.auth import create_access_token, verify_password
from src.api.models.admin_user import AdminUser
from src.api.schemas.auth import TokenResponse


async def login(db: AsyncSession, username: str, password: str) -> TokenResponse:
    """
    Verify credentials and return a JWT access token.
    Raises 401 if credentials are invalid.
    """
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == username)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token)
