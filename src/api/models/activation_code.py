"""
ActivationCode — códigos de activación generados por el admin para regalar suscripciones.
"""
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from src.core.database import Base


class ActivationCode(Base):
    __tablename__ = "activation_codes"

    # Código alfanumérico único (ej: ABCD-1234-EFGH)
    code = Column(String, primary_key=True, index=True)

    # Duración en días que otorga el código (por defecto 365 = 1 año)
    duration_days = Column(Integer, nullable=False, default=365)

    # Nota del admin (opcional)
    note = Column(String, nullable=True)

    # Cuándo fue creado
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Quién lo usó (device_id) — NULL si aún no se ha usado
    used_by_device = Column(String, nullable=True)

    # Cuándo fue usado
    used_at = Column(DateTime, nullable=True)
