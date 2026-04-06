"""SQLAlchemy ORM model for DevicePlaylist."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DevicePlaylist(Base):
    """
    Stores an m3u8 playlist associated with a device MAC address.

    ``type='file'`` → ``content`` contains the raw m3u8 text.
    ``type='url'``  → ``content`` contains the remote URL.
    ``pending_clear`` → when True, the Android app must wipe all local data on next sync.
    """

    __tablename__ = "device_playlists"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mac: Mapped[str] = mapped_column(String(17), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(4), nullable=False)  # 'file' | 'url'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    pending_clear: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
