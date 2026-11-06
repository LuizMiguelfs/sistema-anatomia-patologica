from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

#todo: ge e le são restrições temporarias, depois dos testes e tals implementar as regras de negocios

#! restringe a origem dos dados pra quando dados forem demonstrativos
class OrigemDados(str, Enum):
    DEMONSTRACAO = "demonstracao"
    BANCO_DADOS = "banco_dados"
    INDISPONIVEL = "indisponivel"

#! acompanhamento dos casos
class ResumoOperacional(BaseModel):
    total_casos: int | None = Field(default=None, ge=0)
    casos_pendentes: int | None = Field(default=None, ge=0)
    casos_atrasados: int | None = Field(default=None, ge=0)
    aguardando_complementacao: int | None = Field(
        default=None, ge=0
    )

#! indicadores associados
class IndicadoresGerenciais(BaseModel):
    tempo_medio_liberacao_horas: float | None = Field(
        default=None, ge=0
    )
    percentual_cumprimento_prazo: float | None = Field(
        default=None, ge=0, le=100
    )
    percentual_automacao: float | None = Field(
        default=None, ge=0, le=100
    )
    percentual_rastreabilidade: float | None = Field(
        default=None, ge=0, le=100
    )
    total_inconsistencias: int | None = Field(
        default=None, ge=0
    )
    total_rejeicoes: int | None = Field(
        default=None, ge=0
    )
    total_erros_transcricao: int | None = Field(
        default=None, ge=0
    )

#! resumo de informações do contrato principal no endpoint
class DashboardResumoResponse(BaseModel):
    origem_dados: OrigemDados
    atualizado_em: datetime #* momento do ultimo processamento do dashboard
    operacional: ResumoOperacional
    gerencial: IndicadoresGerenciais