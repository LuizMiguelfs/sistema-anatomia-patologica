"""Contrato do dashboard: valores não medidos são NULL, nunca estimados."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class OrigemDados(str, Enum):
    DEMONSTRACAO = "demonstracao"
    BANCO_DADOS = "banco_dados"
    INDISPONIVEL = "indisponivel"


class ResumoOperacional(BaseModel):
    total_casos: int | None = Field(default=None, ge=0)
    casos_pendentes: int | None = Field(default=None, ge=0)
    casos_atrasados: int | None = Field(default=None, ge=0)
    aguardando_complementacao: int | None = Field(default=None, ge=0)


class IndicadoresGerenciais(BaseModel):
    tempo_medio_liberacao_horas: float | None = Field(default=None, ge=0)
    percentual_cumprimento_prazo: float | None = Field(default=None, ge=0, le=100)
    percentual_automacao: float | None = Field(default=None, ge=0, le=100)
    percentual_rastreabilidade: float | None = Field(default=None, ge=0, le=100)
    total_inconsistencias: int | None = Field(default=None, ge=0)
    total_rejeicoes: int | None = Field(default=None, ge=0)
    total_erros_transcricao: int | None = Field(default=None, ge=0)


class DashboardResumoResponse(BaseModel):
    origem_dados: OrigemDados
    atualizado_em: datetime
    operacional: ResumoOperacional
    gerencial: IndicadoresGerenciais
    criterios: dict[str, str] = Field(default_factory=dict)
    prazos_horas_por_tipo: dict[str, int] = Field(default_factory=dict)
    prazo_cobertura_casos: int = Field(default=0, ge=0)
