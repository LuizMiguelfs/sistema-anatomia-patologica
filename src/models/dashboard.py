"""Contrato do dashboard: valores não medidos são NULL, nunca estimados."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class OrigemDados(str, Enum):
    DEMONSTRACAO = "demonstracao"
    BANCO_DADOS = "banco_dados"
    INDISPONIVEL = "indisponivel"


class ResumoOperacional(BaseModel):
    total_solicitacoes: int | None = Field(default=None, ge=0)
    solicitacoes_pendentes: int | None = Field(default=None, ge=0)
    solicitacoes_atrasadas: int | None = Field(default=None, ge=0)
    aguardando_complementacao: int | None = Field(default=None, ge=0)


class IndicadoresGerenciais(BaseModel):
    tempo_medio_liberacao_horas: float | None = Field(default=None, ge=0)
    percentual_cumprimento_prazo: float | None = Field(default=None, ge=0, le=100)
    percentual_automacao: float | None = Field(default=None, ge=0, le=100)
    percentual_rastreabilidade: float | None = Field(default=None, ge=0, le=100)
    total_inconsistencias: int | None = Field(default=None, ge=0)
    total_rejeicoes: int | None = Field(default=None, ge=0)
    total_erros_transcricao: int | None = Field(default=None, ge=0)


class FilaFase(BaseModel):
    """Quantas solicitações estão pendentes numa fase agora."""
    etapa: str
    rotulo: str
    grupo: str
    pendentes: int = Field(ge=0)
    urgentes: int = Field(ge=0)
    #: Só nas fases com pré-laudo (Congelação, Microscopia, Revisão); None nas demais.
    aguardando_patologista: int | None = Field(default=None, ge=0)


class RetratoFilas(BaseModel):
    """Retrato das filas no momento da consulta (mesma regra de "pendente" das telas)."""
    nao_retiradas: int = Field(ge=0)
    nao_retiradas_urgentes: int = Field(ge=0)
    urgentes: int = Field(ge=0)
    aguardando_patologista: int = Field(ge=0)
    fases: list[FilaFase] = Field(default_factory=list)


class DashboardResumoResponse(BaseModel):
    origem_dados: OrigemDados
    atualizado_em: datetime
    operacional: ResumoOperacional
    gerencial: IndicadoresGerenciais
    criterios: dict[str, str] = Field(default_factory=dict)
    prazos_horas_por_tipo: dict[str, int] = Field(default_factory=dict)
    prazo_cobertura_solicitacoes: int = Field(default=0, ge=0)
    filas: RetratoFilas | None = None
