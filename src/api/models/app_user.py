"""
AppUser — dispositivo registrado en Cine Tv con trial / suscripción.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from src.core.database import Base


class AppUser(Base):
    __tablename__ = "app_users"

    # Identificador único del dispositivo (UUID generado en la app)
    device_id = Column(String, primary_key=True, index=True)

    # Inicio del periodo de prueba gratuita (7 días)
    trial_start = Column(DateTime, nullable=False, server_default=func.now())

    # Fin de suscripción de pago (NULL = sin suscripción activa)
    subscription_end = Column(DateTime, nullable=True)

    # Fecha de registro
    created_at = Column(DateTime, nullable=False, server_default=func.now())
