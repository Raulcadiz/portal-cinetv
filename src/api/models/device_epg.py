"""SQLAlchemy ORM model for DeviceEpg."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DeviceEpg(Base):
    """
    Stores the XMLTV EPG source for a device MAC address.

    Only **one** EPG source is allowed per MAC — enforced by the unique constraint on ``mac``.
    Saving a new source for an existing MAC replaces the previous record (upsert semantics).

    ``type='file'`` → ``content`` contains the raw XMLTV text.
    ``type='url'``  → ``content`` contains the remote XMLTV URL.
    """

    __tablename__ = "device_epg"
    __table_args__ = (UniqueConstraint("mac", name="uq_device_epg_mac"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mac: Mapped[str] = mapped_column(String(17), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(4), nullable=False)  # 'file' | 'url'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
