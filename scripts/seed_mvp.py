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
from src.controllers import caso_controller, fase_controller, solicitacao_controller
from src.models.authorized_user import AuthorizedUser
from src.providers.implementations.aghu_solicitacao_simulado_provider import AghuSolicitacaoSimuladoProvider
from src.providers.implementations.caso_sqlite_provider import CasoSqliteProvider

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


async def _abrir_todas(provider: CasoSqliteProvider, aghu: AghuSolicitacaoSimuladoProvider) -> List[Dict[str, Any]]:
    """Abre todas as solicitações fictícias (recebidas), como a Recepção faria."""
    casos = []
    for numero in aghu.listar_numeros():
        casos.append(await caso_controller.abrir_caso(numero, REC, "127.0.0.1", provider, aghu))
    return casos


async def _datas_de_recebimento(session, casos: List[Dict[str, Any]]) -> None:
    """Espalha o recebimento pelos últimos 4 dias, para a ordem das filas ficar realista."""
    inicio = datetime.now(timezone.utc) - timedelta(days=4)
    passo = timedelta(days=4) / max(len(casos), 1)
    for i, caso in enumerate(casos):
        quando = (inicio + passo * i).isoformat()
        await session.execute(text("UPDATE casos SET criado_em = :q WHERE id = :id"), {"q": quando, "id": caso["id"]})
        await session.execute(
            text("UPDATE caso_movimentacoes SET criado_em = :q WHERE caso_id = :id AND tipo = 'ABERTURA'"),
            {"q": quando, "id": caso["id"]},
        )
    await session.commit()


async def _avancar(provider: CasoSqliteProvider, casos: List[Dict[str, Any]]) -> None:
    """Leva parte das solicitações por algumas fases, deixando pendências em todas as filas."""
    por_tipo: Dict[str, List[Dict[str, Any]]] = {}
    for caso in casos:
        por_tipo.setdefault(caso["tipo_exame"], []).append(caso)

    async def retirar(caso):
        await solicitacao_controller.marcar_retirado(caso["id"], REC, "127.0.0.1", provider)

    async def concluir(etapa, caso, usuario, dados):
        await fase_controller.concluir_fase(etapa, caso["id"], dados, usuario, "127.0.0.1", provider)

    async def salvar(etapa, caso, usuario, dados):
        await fase_controller.salvar_fase(etapa, caso["id"], dados, usuario, "127.0.0.1", provider)

    # HP: 5 ficam em "Não retirados"; as demais se espalham por Macroscopia, Processamento e Microscopia.
    hp = por_tipo.get("HP", [])
    for i, caso in enumerate(hp[5:]):
        await retirar(caso)
        if i % 6 == 0:
            continue  # Macroscopia pendente, sem nada salvo
        if i % 6 == 1:
            await salvar("MACROSCOPIA", caso, RES, {"descricao_macroscopica": MACRO["descricao_macroscopica"]})
            continue  # Macroscopia com rascunho
        await concluir("MACROSCOPIA", caso, RES, MACRO)
        if i % 6 == 2:
            continue  # Processamento pendente
        await concluir("PROCESSAMENTO", caso, LAB, PROC_HP)
        if i % 6 == 3:
            continue  # Microscopia pendente
        if i % 6 == 4:
            await salvar("MICROSCOPIA", caso, RES, {"pre_laudo": MICRO["pre_laudo"]})
            continue  # pré-laudo salvo, aguardando o patologista
        await concluir("MICROSCOPIA", caso, PAT, MICRO)  # arquivada

    # Uma HP na Microscopia com IHQ pedida (encaminhamento): aparece na fila da IHQ.
    micro_pendentes = [c for c in hp[5:] if (await provider.buscar_por_id(c["id"]))["etapa_atual"] == "MICROSCOPIA"]
    if micro_pendentes:
        await caso_controller.encaminhar_caso(
            micro_pendentes[0]["id"], "IHQ", "Painel imuno-histoquímico para definição diagnóstica", PAT, "127.0.0.1", provider,
        )

    # Congelação: 1 em "Não retirados" (urgente), 2 pendentes, 1 concluída.
    co = por_tipo.get("CO", [])
    for i, caso in enumerate(co[1:]):
        await retirar(caso)
        if i == 2:
            await concluir("CONGELACAO", caso, PAT, {
                "analise_preliminar": "Nódulo firme, esbranquiçado, 1,5 cm.",
                "resultado": "Negativo para malignidade na amostra examinada.", "bloco_avisado": True,
            })

    # Citologia: 1 de cada em "Não retirados"; as demais no Processamento ou na Microscopia.
    for tipo in ("CG", "CCV"):
        for i, caso in enumerate(por_tipo.get(tipo, [])[1:]):
            await retirar(caso)
            if i % 2 == 1:
                await concluir("PROCESSAMENTO", caso, LAB, PROC_CITO)

    # IHQ e Revisão de Lâmina: 1 de cada em "Não retirados"; as demais nas suas filas.
    for tipo in ("IHQ", "RL"):
        for caso in por_tipo.get(tipo, [])[1:]:
            await retirar(caso)


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
            total = (await session.execute(text("SELECT COUNT(*) FROM casos"))).scalar()
            if total:
                raise SystemExit("O banco já tem solicitações. Para recomeçar, apague data/app.db e rode de novo.")
            await _usuarios(session)
            provider = CasoSqliteProvider(session)
            aghu = AghuSolicitacaoSimuladoProvider(settings.AGHU_SIMULADO_PATH)
            casos = await _abrir_todas(provider, aghu)
            await _datas_de_recebimento(session, casos)
            await _avancar(provider, casos)
        print(f"Carga concluída: {len(casos)} solicitações fictícias e {len(USUARIOS)} usuários de demonstração.")
        print("Usuários: " + ", ".join(f"{u} ({p})" for u, p in USUARIOS.items()))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    main()
