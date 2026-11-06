"""Configuração central. Falha imediatamente se produção não for segura."""
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENV = os.getenv("ENV", "development").lower()
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()
    RAW_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS = [x.strip() for x in RAW_ALLOWED_ORIGINS.split(",") if x.strip()]
    PACIENTE_PROVIDER_TYPE = os.getenv("PACIENTE_PROVIDER_TYPE", "POSTGRES").upper()
    APP_DB_URL = os.getenv("APP_DB_URL", "sqlite+aiosqlite:///data/app.db")
    POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
    ORACLE_DSN = os.getenv("ORACLE_DSN", "")
    AD_URL = os.getenv("AD_URL", "")
    AD_BASEDN = os.getenv("AD_BASEDN", "DC=ebserhnet,DC=gov,DC=br")
    AD_BIND_USER = os.getenv("AD_BIND_USER", "")
    AD_BIND_PASSWORD = os.getenv("AD_BIND_PASSWORD", "")
    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", "24"))  # compatibilidade
    ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "30"))
    SESSION_REFRESH_HOURS = int(os.getenv("SESSION_REFRESH_HOURS", "12"))

    @classmethod
    def validate_config(cls):
        if cls.ENV not in {"development", "testing", "test", "production"}:
            raise RuntimeError("ENV deve ser development, testing ou production")
        if cls.ACCESS_TOKEN_MINUTES < 1 or cls.REFRESH_TOKEN_EXP_DAYS < 1 or cls.SESSION_REFRESH_HOURS < 1:
            raise RuntimeError("Configuração de validade de tokens inválida")
        if len(cls.JWT_SECRET) < 32:
            raise RuntimeError("JWT_SECRET deve ter pelo menos 32 caracteres")
        if cls.ENV == "production":
            banned = {"super-secret-key-change-in-production", "SUA_CHAVE_SECRETA_SUPER_FORTE_AQUI_ALTERAR_EM_PRODUCAO"}
            if len(cls.JWT_SECRET) < 32 or cls.JWT_SECRET in banned:
                raise RuntimeError("JWT_SECRET forte é obrigatório em produção")
            if urlparse(cls.AD_URL).scheme != "ldaps":
                raise RuntimeError("Produção requer AD_URL com LDAPS")
            if not cls.AD_BASEDN or not (cls.AD_BIND_USER and cls.AD_BIND_PASSWORD):
                raise RuntimeError("AD_BASEDN e conta de serviço são obrigatórios em produção")
            if not cls.ALLOWED_ORIGINS or "*" in cls.ALLOWED_ORIGINS:
                raise RuntimeError("ALLOWED_ORIGINS explícito é obrigatório em produção")


settings = Settings()
settings.validate_config()
