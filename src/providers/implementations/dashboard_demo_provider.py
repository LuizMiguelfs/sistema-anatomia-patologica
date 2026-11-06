from datetime import datetime, timezone
from src.models.dashboard import (DashboardResumoResponse,IndicadoresGerenciais, OrigemDados, ResumoOperacional,)
from src.providers.interfaces.dashboard_provider_interface import (DashboardProviderInterface,)

#! implementar o tal obter_resumo (metodo abstrato da interface) com dados demonstrativos
class DashboardDemoProvider(DashboardProviderInterface):
    async def obter_resumo(self) -> DashboardResumoResponse:
        """Resumo demonstrativo do painel (dados fixos, não reais)."""
        return DashboardResumoResponse(
            origem_dados=OrigemDados.DEMONSTRACAO,
            atualizado_em=datetime.now(timezone.utc),
            operacional=ResumoOperacional(
                total_casos=120,
                casos_pendentes=38,
                casos_atrasados=12,
                aguardando_complementacao=8,
            ),
            gerencial=IndicadoresGerenciais(
                tempo_medio_liberacao_horas=48.5,
                percentual_cumprimento_prazo=87.5,
                percentual_automacao=72.0,
                percentual_rastreabilidade=96.0,
                total_inconsistencias=6,
                total_rejeicoes=4,
                total_erros_transcricao=3,
            ),
        )