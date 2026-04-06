"""
Async SQLAlchemy engine, session factory and base model for IPTVSur Portal.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    # echo=True enables SQL logging — useful in development, disable in production
    echo=False,
    # SQLite-specific: check_same_thread=False required for async usage
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    Import this in each model file and inherit from it.
    """
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session per request.

    Usage::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Table creation (used in lifespan) ────────────────────────────────────────
async def create_tables() -> None:
    """
    Creates all database tables defined via SQLAlchemy models.
    Called once on application startup.

    In production, consider using Alembic migrations instead of create_all.
    """
    # Import models to register them with Base.metadata before create_all
    from src.api.models import device_playlist, device_epg, admin_user  # noqa: F401
    from src.api.models import app_user, activation_code, user_list      # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
