"""Admin authentication routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middlewares.auth import hash_password
from src.api.models.admin_user import AdminUser
from src.api.schemas.auth import LoginRequest, TokenResponse
from src.api.services.auth_service import login
from src.core.database import get_db

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str


@router.post(
    "/register",
    status_code=201,
    summary="Register first admin (only if no admins exist)",
)
async def register_first_admin(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(select(func.count()).select_from(AdminUser))
    if count_result.scalar_one() > 0:
        raise HTTPException(status_code=403, detail="Registro no permitido. Ya existe un admin.")

    admin = AdminUser(username=body.username, hashed_password=hash_password(body.password))
    db.add(admin)
    await db.commit()
    return {"message": "Admin creado exitosamente"}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Admin login — obtain JWT access token",
)
async def admin_login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await login(db, body.username, body.password)
