"""Autorização local SAP: a identidade vem do AD, o perfil é concedido localmente."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from ..resources.database import Base


class AuthorizedUser(Base):
    __tablename__ = "authorized_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(128), unique=True, index=True, nullable=False)
    nome = Column(String(200), nullable=True)  # nome de exibição vindo do AD na inclusão
    role = Column(String(32), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)
