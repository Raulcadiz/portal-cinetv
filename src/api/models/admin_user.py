"""SQLAlchemy ORM model for AdminUser."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AdminUser(Base):
    """Portal administrator. Created via the seed script or ``create_admin`` helper."""

    __tablename__ = "admin_users"
    __table_args__ = (UniqueConstraint("username", name="uq_admin_users_username"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
