"""Refresh tokens: armazenar APENAS SHA-256 do segredo aleatório, nunca o cookie cru.

Compatibilidade de esquema: a coluna `token` existente é reutilizada para o hash.
Tokens legados em texto puro deixam de ser aceitos e devem ser revogados.
`groups` é JSON com metadados não sensíveis: {"remember_me": bool}.

Sem exclusão física (SPEC.md / 06-arquitetura.md): token usado na renovação ou no logout
recebe `deleted_at` e deixa de ser aceito; a linha permanece no banco.
"""
from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func
from ..resources.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), index=True, nullable=False)
    token = Column(String(64), unique=True, index=True, nullable=False)
    groups = Column(JSON, nullable=True)  # Mantido por compatibilidade com banco existente.
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)  # exclusão lógica: preenchido ao revogar
