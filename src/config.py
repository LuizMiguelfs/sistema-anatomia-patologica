"""Configuração central. Falha imediatamente se produção não for segura."""
import os
import json
from urllib.parse import urlparse
from dotenv import load_dotenv

from .helpers.crypto_helper import validar_chave

load_dotenv()


class Settings:
    ENV = os.getenv("ENV", "development").lower()
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()
    RAW_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS = [x.strip() for x in RAW_ALLOWED_ORIGINS.split(",") if x.strip()]

    APP_DB_URL = os.getenv("APP_DB_URL", "sqlite+aiosqlite:///data/app.db")
    POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
    # PR 1: pacientes. Usa CSV se POSTGRES_DSN nao estiver configurado.
    PACIENTE_PROVIDER_TYPE = (
        os.getenv("PACIENTE_PROVIDER_TYPE", "").strip()
        or ("POSTGRES" if POSTGRES_DSN else "CSV")
    ).upper()
    PACIENTE_CSV_PATH = os.getenv("PACIENTE_CSV_PATH", "data/pacientes.csv")
    # Solicitações do AGHU: POSTGRES (AGHU Slave) ou SIMULADO (JSON fictício, só fora de produção).
    AGHU_PROVIDER_TYPE = (
        os.getenv("AGHU_PROVIDER_TYPE", "").strip()
        or ("POSTGRES" if POSTGRES_DSN else "SIMULADO")
    ).upper()
    AGHU_SIMULADO_PATH = os.getenv("AGHU_SIMULADO_PATH", "data/aghu_simulado.json")
    # Invariante: SAP nunca escreve na origem AGHU, independente de ambiente.
    PACIENTE_POSTGRES_ESCRITA = False
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
    # Chave AES-256 dos dados sensíveis gravados pelo SAP (32 bytes em base64).
    SAP_DATA_KEY = os.getenv("SAP_DATA_KEY", "")
    # Horas corridas DESDE ABERTURA DO CASO, apenas se a Chefia validar o critério.
    SAP_PRAZOS_EXAME_HORAS = os.getenv("SAP_PRAZOS_EXAME_HORAS", "{}")

    @classmethod
    def prazos_exame_horas(cls) -> dict[str, int]:
        """Prazos aprovados no ambiente, sem defaults clínicos inventados."""
        try:
            dados = json.loads(cls.SAP_PRAZOS_EXAME_HORAS)
            if not isinstance(dados, dict) or any(
                k not in {"HP", "CO", "CG", "CCV"} or type(v) is not int or not 1 <= v <= 100000
                for k, v in dados.items()
            ):
                raise ValueError()
            return dados
        except (ValueError, TypeError) as exc:
            raise RuntimeError("SAP_PRAZOS_EXAME_HORAS deve ser JSON de horas inteiras positivas por tipo de exame") from exc

    @classmethod
    def validate_config(cls) -> None:
        """Valida as variáveis de ambiente na inicialização; falha imediatamente se a configuração for insegura."""
        if cls.ENV not in {"development", "testing", "test", "production"}:
            raise RuntimeError("ENV deve ser development, testing ou production")
        if cls.ACCESS_TOKEN_MINUTES < 1 or cls.REFRESH_TOKEN_EXP_DAYS < 1 or cls.SESSION_REFRESH_HOURS < 1:
            raise RuntimeError("Configuração de validade de tokens inválida")
        if len(cls.JWT_SECRET) < 32:
            raise RuntimeError("JWT_SECRET deve ter pelo menos 32 caracteres")
        validar_chave(cls.SAP_DATA_KEY)  # AES-256 obrigatório em todos os ambientes (SPEC.md)
        cls.prazos_exame_horas()
        if cls.AGHU_PROVIDER_TYPE not in {"POSTGRES", "SIMULADO"}:
            raise RuntimeError("AGHU_PROVIDER_TYPE deve ser POSTGRES ou SIMULADO")
        if cls.ENV == "production":
            if cls.AGHU_PROVIDER_TYPE != "POSTGRES":
                raise RuntimeError("Produção exige solicitações do AGHU real (AGHU_PROVIDER_TYPE=POSTGRES)")
            if cls.PACIENTE_PROVIDER_TYPE != "POSTGRES" or not cls.POSTGRES_DSN:
                raise RuntimeError("Produção exige catálogo de pacientes AGHU via POSTGRES_DSN")
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
