"""Carga de DEMONSTRAÇÃO do MVP: usuários por perfil e solicitações FICTÍCIAS em várias fases.

Usa as mesmas regras do sistema (controllers), então tudo fica com movimentação e auditoria.
Só roda fora de produção, com o AGHU SIMULADO e num banco sem solicitações.

Uso (na raiz do projeto, com o .env de desenvolvimento):
    python -m scripts.seed_mvp --confirm

Para recomeçar do zero, apague o banco local de desenvolvimento (data/app.db) e rode de novo.
Login de demonstração: os usuários abaixo, com a senha de MOCK_AUTH_PASSWORD, desde que
MOCK_AUTH_USERS contenha esses logins (ver .env.example).
"""
import argparse
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.controllers import fase_controller, retirada_controller, solicitacao_controller
from src.models.authorized_user import AuthorizedUser
from src.providers.implementations.aghu_solicitacao_simulado_provider import AghuSolicitacaoSimuladoProvider
from src.providers.implementations.solicitacao_sqlite_provider import SolicitacaoSqliteProvider

#: Usuários de demonstração (login -> perfil).
USUARIOS = {
    "demo.recepcao": "RECEPCAO",
    "demo.residente": "RESIDENTE",
    "demo.patologista": "PRECEPTORIA",
    "demo.laboratorio": "LABORATORIO",
    "demo.chefia": "CHEFIA",
}
REC = {"username": "demo.recepcao", "role": "RECEPCAO"}
RES = {"username": "demo.residente", "role": "RESIDENTE"}
PAT = {"username": "demo.patologista", "role": "PRECEPTORIA"}
LAB = {"username": "demo.laboratorio", "role": "LABORATORIO"}

MACRO = {
    "descricao_macroscopica": "Fragmento irregular, pardacento, medindo 1,2 x 0,8 x 0,5 cm.",
    "qtd_fragmentos": 2, "qtd_cassetes": 1,
    "laudo_macroscopico": "Material recebido em formol, identificado. Incluído em totalidade.",
}
PROC_HP = {"inicio": "Histotécnico", "qtd_blocos": 1, "qtd_laminas": 2, "coloracao": "HE"}
PROC_CITO = {"material_liquido": True, "cell_block": False, "qtd_laminas": 2, "coloracao": "Papanicolaou"}
MICRO = {"pre_laudo": "Mucosa com processo inflamatório crônico inespecífico.",
         "diagnostico": "Processo inflamatório crônico inespecífico. Ausência de malignidade nesta amostra."}


def _argumentos() -> argparse.Namespace:
    """Lê os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description="Carga de demonstração do MVP (dados fictícios)")
    parser.add_argument("--confirm", action="store_true", help="Confirma a carga no banco local de desenvolvimento")
    return parser.parse_args()


async def _usuarios(session) -> None:
    """Cria (ou reativa) os usuários de demonstração no banco local."""
    for login, perfil in USUARIOS.items():
        existente = (await session.execute(select(AuthorizedUser).where(AuthorizedUser.username == login))).scalar_one_or_none()
        if existente:
            existente.role, existente.active = perfil, True
        else:
            session.add(AuthorizedUser(username=login, role=perfil, active=True, nome=f"Demonstração {perfil.title()}"))
    await session.commit()


async def _abrir_todas(provider: SolicitacaoSqliteProvider, aghu: AghuSolicitacaoSimuladoProvider) -> List[Dict[str, Any]]:
    """Abre todas as solicitações fictícias (recebidas), como a Recepção faria."""
    solicitacoes = []
    for numero in aghu.listar_numeros():
        solicitacoes.append(await solicitacao_controller.abrir_solicitacao(numero, REC, "127.0.0.1", provider, aghu))
    return solicitacoes


async def _datas_de_recebimento(session, solicitacoes: List[Dict[str, Any]]) -> None:
    """Espalha o recebimento pelos últimos 4 dias, para a ordem das filas ficar realista."""
    inicio = datetime.now(timezone.utc) - timedelta(days=4)
    passo = timedelta(days=4) / max(len(solicitacoes), 1)
    for i, solicitacao in enumerate(solicitacoes):
        quando = (inicio + passo * i).isoformat()
        await session.execute(text("UPDATE solicitacoes_exame SET criado_em = :q WHERE id = :id"), {"q": quando, "id": solicitacao["id"]})
        await session.execute(
            text("UPDATE solicitacao_movimentacoes SET criado_em = :q WHERE solicitacao_id = :id AND tipo = 'ABERTURA'"),
            {"q": quando, "id": solicitacao["id"]},
        )
    await session.commit()


async def _avancar(provider: SolicitacaoSqliteProvider, solicitacoes: List[Dict[str, Any]]) -> None:
    """Leva parte das solicitações por algumas fases, deixando pendências em todas as filas."""
    por_tipo: Dict[str, List[Dict[str, Any]]] = {}
    for solicitacao in solicitacoes:
        por_tipo.setdefault(solicitacao["tipo_exame"], []).append(solicitacao)

    async def retirar(solicitacao):
        await retirada_controller.marcar_retirado(solicitacao["id"], REC, "127.0.0.1", provider)

    async def concluir(etapa, solicitacao, usuario, dados):
        await fase_controller.concluir_fase(etapa, solicitacao["id"], dados, usuario, "127.0.0.1", provider)

    async def salvar(etapa, solicitacao, usuario, dados):
        await fase_controller.salvar_fase(etapa, solicitacao["id"], dados, usuario, "127.0.0.1", provider)

    # HP: 5 ficam em "Não retirados"; as demais se espalham por Macroscopia, Processamento e Microscopia.
    hp = por_tipo.get("HP", [])
    for i, solicitacao in enumerate(hp[5:]):
        await retirar(solicitacao)
        if i % 6 == 0:
            continue  # Macroscopia pendente, sem nada salvo
        if i % 6 == 1:
            await salvar("MACROSCOPIA", solicitacao, RES, {"descricao_macroscopica": MACRO["descricao_macroscopica"]})
            continue  # Macroscopia com rascunho
        await concluir("MACROSCOPIA", solicitacao, RES, MACRO)
        if i % 6 == 2:
            continue  # Processamento pendente
        await concluir("PROCESSAMENTO", solicitacao, LAB, PROC_HP)
        if i % 6 == 3:
            continue  # Microscopia pendente
        if i % 6 == 4:
            await salvar("MICROSCOPIA", solicitacao, RES, {"pre_laudo": MICRO["pre_laudo"]})
            continue  # pré-laudo salvo, aguardando o patologista
        await concluir("MICROSCOPIA", solicitacao, PAT, MICRO)  # arquivada

    # Uma HP na Microscopia com IHQ pedida (encaminhamento): aparece na fila da IHQ.
    micro_pendentes = [c for c in hp[5:] if (await provider.buscar_por_id(c["id"]))["etapa_atual"] == "MICROSCOPIA"]
    if micro_pendentes:
        await solicitacao_controller.encaminhar_solicitacao(
            micro_pendentes[0]["id"], "IHQ", "Painel imuno-histoquímico para definição diagnóstica", PAT, "127.0.0.1", provider,
        )

    # Congelação: 1 em "Não retirados" (urgente), 2 pendentes, 1 concluída.
    co = por_tipo.get("CO", [])
    for i, solicitacao in enumerate(co[1:]):
        await retirar(solicitacao)
        if i == 2:
            await concluir("CONGELACAO", solicitacao, PAT, {
                "analise_preliminar": "Nódulo firme, esbranquiçado, 1,5 cm.",
                "resultado": "Negativo para malignidade na amostra examinada.", "bloco_avisado": True,
            })

    # Citologia: 1 de cada em "Não retirados"; as demais no Processamento ou na Microscopia.
    for tipo in ("CG", "CCV"):
        for i, solicitacao in enumerate(por_tipo.get(tipo, [])[1:]):
            await retirar(solicitacao)
            if i % 2 == 1:
                await concluir("PROCESSAMENTO", solicitacao, LAB, PROC_CITO)

    # IHQ e Revisão de Lâmina: 1 de cada em "Não retirados"; as demais nas suas filas.
    for tipo in ("IHQ", "RL"):
        for solicitacao in por_tipo.get(tipo, [])[1:]:
            await retirar(solicitacao)


def main() -> None:
    """Valida o ambiente, aplica as migrações e executa a carga de demonstração."""
    args = _argumentos()
    if not args.confirm:
        raise SystemExit("Nada foi feito. Rode com --confirm para carregar os dados fictícios.")
    if settings.ENV == "production":
        raise SystemExit("A carga de demonstração não roda em produção.")
    if settings.AGHU_PROVIDER_TYPE != "SIMULADO":
        raise SystemExit("A carga de demonstração exige AGHU_PROVIDER_TYPE=SIMULADO.")
    os.makedirs("data", exist_ok=True)
    command.upgrade(Config("alembic.ini"), "head")  # fora do loop assíncrono (o env.py do Alembic usa asyncio.run)
    asyncio.run(_carga(os.getenv("SQLITE_DSN") or settings.APP_DB_URL))


async def _carga(dsn: str) -> None:
    """Cria usuários, abre as solicitações fictícias e as distribui pelas fases."""
    engine = create_async_engine(dsn)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with fabrica() as session:
            total = (await session.execute(text("SELECT COUNT(*) FROM solicitacoes_exame"))).scalar()
            if total:
                raise SystemExit("O banco já tem solicitações. Para recomeçar, apague data/app.db e rode de novo.")
            await _usuarios(session)
            provider = SolicitacaoSqliteProvider(session)
            aghu = AghuSolicitacaoSimuladoProvider(settings.AGHU_SIMULADO_PATH)
            solicitacoes = await _abrir_todas(provider, aghu)
            await _datas_de_recebimento(session, solicitacoes)
            await _avancar(provider, solicitacoes)
        print(f"Carga concluída: {len(solicitacoes)} solicitações fictícias e {len(USUARIOS)} usuários de demonstração.")
        print("Usuários: " + ", ".join(f"{u} ({p})" for u, p in USUARIOS.items()))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    main()
