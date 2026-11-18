"""Dashboard calculado exclusivamente sobre eventos observáveis do banco local SAP."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.dashboard import (
    DashboardResumoResponse, IndicadoresGerenciais, OrigemDados, ResumoOperacional,
)
from ..interfaces.dashboard_provider_interface import DashboardProviderInterface
from .solicitacao_sqlite_provider import get_sql_query


CRITERIOS: dict[str, str] = {
    "total_solicitacoes": "Todas as solicitações ativas do SAP desde o início do registro (sem filtro de período).",
    "solicitacoes_pendentes": "Solicitações ativas do SAP cujo status não é ARQUIVADO, independentemente de etapa ou idade.",
    "solicitacoes_atrasadas": (
        "Solicitações não arquivadas em que o tempo corrido desde a abertura da solicitação no SAP "
        "supera o prazo em horas configurado para o tipo de exame. "
        "Sem prazos para TODAS as solicitações pendentes, o número não é exibido. "
        "Não representa o prazo clínico desde a coleta; validar marco inicial com a Chefia."
    ),
    "aguardando_complementacao": "Não mensurado: falta um evento estruturado de solicitação/retorno de complemento.",
    "tempo_medio_liberacao_horas": "Não mensurado: falta data/hora de liberação do laudo no AGHU para calcular a média.",
    "percentual_cumprimento_prazo": (
        "Não mensurado: exige marco inicial, data de liberação do laudo e SLA aprovado por tipo "
        "para a mesma população de solicitações. Não confundir arquivo da solicitação com liberação."
    ),
    "percentual_automacao": "Não mensurado: é preciso instrumentar campos recuperados do AGHU e total de campos elegíveis.",
    "percentual_rastreabilidade": "Não mensurado: requer conjunto mínimo aprovado de eventos rastreáveis por material.",
    "total_inconsistencias": "Número de inconformidades abertas vinculadas a solicitações ativas do SAP.",
    "total_rejeicoes": "Não mensurado: é necessário evento estruturado de rejeição de material.",
    "total_erros_transcricao": "Não mensurado: é necessário registrar divergências de transcrição confirmadas.",
}


class DashboardSqliteProvider(DashboardProviderInterface):
    """Consulta apenas tabelas locais; nunca depende da disponibilidade do AGHU."""

    def __init__(self, session: AsyncSession, prazos: dict[str, int] | None = None) -> None:
        self.session = session
        self.prazos = prazos or {}

    async def obter_resumo(self) -> DashboardResumoResponse:
        """Produz agregados, sem inventar medidas ainda não instrumentadas."""
        agora = datetime.now(timezone.utc)
        rows = (await self.session.execute(text(get_sql_query("solicitacao/dashboard_solicitacoes.sql")))).mappings().all()
        quantidade_inconformidades = (
            await self.session.execute(text(get_sql_query("solicitacao/dashboard_inconformidades.sql")))
        ).scalar_one()
        ativos = [r for r in rows if r["status"] != "ARQUIVADO"]
        com_prazo = [r for r in ativos if r["tipo_exame"] in self.prazos]
        atrasados: int | None = None
        if len(com_prazo) == len(ativos):
            atrasados = 0
            for solicitacao in ativos:
                try:
                    inicio = datetime.fromisoformat(solicitacao["criado_em"])
                    if inicio.tzinfo is None:
                        # Registros antigos sem timezone não são confiáveis para SLA.
                        atrasados = None
                        break
                    duracao_horas = (agora - inicio.astimezone(timezone.utc)).total_seconds() / 3600
                except (ValueError, TypeError, OverflowError):
                    atrasados = None
                    break
                if duracao_horas > self.prazos[solicitacao["tipo_exame"]]:
                    atrasados += 1

        return DashboardResumoResponse(
            origem_dados=OrigemDados.BANCO_DADOS,
            atualizado_em=agora,
            operacional=ResumoOperacional(
                total_solicitacoes=len(rows), solicitacoes_pendentes=len(ativos),
                solicitacoes_atrasadas=atrasados, aguardando_complementacao=None,
            ),
            gerencial=IndicadoresGerenciais(total_inconsistencias=quantidade_inconformidades),
            criterios=CRITERIOS,
            prazos_horas_por_tipo=self.prazos,
            prazo_cobertura_solicitacoes=len(com_prazo),
        )
