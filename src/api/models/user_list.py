"""
UserList — listas IPTV (URL o Xtream Codes) asociadas a un dispositivo.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.sql import func

from src.core.database import Base


class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # Dispositivo propietario
    device_id = Column(String, nullable=False, index=True)

    # Nombre descriptivo de la lista
    name = Column(String, nullable=True)

    # Tipo: 'url' | 'xtream' | 'file'
    list_type = Column(String, nullable=False)

    # Para type='url': URL directa al M3U/M3U8
    url = Column(Text, nullable=True)

    # Para type='xtream': credenciales Xtream Codes
    xtream_server = Column(String, nullable=True)
    xtream_user   = Column(String, nullable=True)
    xtream_pass   = Column(String, nullable=True)

    # Para type='file': contenido M3U subido
    content = Column(Text, nullable=True)

    # Grupos seleccionados (JSON array de strings); NULL = todos
    selected_groups = Column(Text, nullable=True)

    # Si esta lista es la activa en el dispositivo
    is_active = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
