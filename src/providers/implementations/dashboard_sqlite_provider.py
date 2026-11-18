"""Dashboard calculado exclusivamente sobre eventos observáveis do banco local SAP."""
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.formularios_fase import CAMPO_PRE_LAUDO, FASES
from ...models.dashboard import (
    DashboardResumoResponse, FilaFase, IndicadoresGerenciais, OrigemDados, ResumoOperacional, RetratoFilas,
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
    "filas": (
        "Retrato das filas agora: não retiradas (Recepção), pendentes e urgentes de cada fase, com a mesma "
        "regra das telas. Aguardando o patologista = pendente na Congelação, Microscopia ou Revisão de Lâmina "
        "com rascunho salvo e o pré-laudo (na Congelação, a análise preliminar) preenchido."
    ),
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

        filas = await self._retrato_filas()
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
            filas=filas,
        )

    async def _retrato_filas(self) -> RetratoFilas:
        """Pendentes, urgentes e aguardando o patologista em cada fila, agora (só contagens)."""
        linhas = (await self.session.execute(
            text(get_sql_query("solicitacao/dashboard_filas.sql")),
            {"campos_pre_laudo": json.dumps(CAMPO_PRE_LAUDO)},
        )).mappings().all()
        por_etapa = {linha["etapa"]: linha for linha in linhas}
        fases = []
        for fase in FASES:  # ordem do menu
            linha = por_etapa.get(fase["etapa"]) or {}
            fases.append(FilaFase(
                etapa=fase["etapa"], rotulo=fase["rotulo"], grupo=fase["grupo"],
                pendentes=linha.get("pendentes") or 0, urgentes=linha.get("urgentes") or 0,
                aguardando_patologista=(linha.get("aguardando_patologista") or 0) if fase["etapa"] in CAMPO_PRE_LAUDO else None,
            ))
        recepcao = por_etapa.get("RECEPCAO") or {}
        nao_retiradas_urgentes = recepcao.get("nao_retiradas_urgentes") or 0
        return RetratoFilas(
            nao_retiradas=recepcao.get("nao_retiradas") or 0,
            nao_retiradas_urgentes=nao_retiradas_urgentes,
            urgentes=nao_retiradas_urgentes + sum(f.urgentes for f in fases),
            aguardando_patologista=sum(f.aguardando_patologista or 0 for f in fases),
            fases=fases,
        )
