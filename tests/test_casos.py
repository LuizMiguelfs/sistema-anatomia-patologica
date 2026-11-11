"""Testes do módulo de Casos (UC002, UC012, UC017, UC018, UC019).

Usam providers em memória: validam as regras de negócio do Controller sem
depender de banco, AGHU ou HTTP.
"""
from typing import Any, Dict, List, Optional

import pytest
from fastapi import HTTPException

from src.controllers import caso_controller as ctrl

pytestmark = pytest.mark.asyncio

RECEPCAO = {"username": "ana.recepcao", "role": "RECEPCAO"}
LAB = {"username": "bia.lab", "role": "LABORATORIO"}
RESIDENTE = {"username": "caio.res", "role": "RESIDENTE"}

HP = {
    ("INICIO", "AVANCO"): ["RECEPCAO"], ("RECEPCAO", "AVANCO"): ["MACROSCOPIA"],
    ("MACROSCOPIA", "AVANCO"): ["PROCESSAMENTO"], ("PROCESSAMENTO", "AVANCO"): ["MICROSCOPIA"],
    ("MICROSCOPIA", "AVANCO"): ["ARQUIVO"],
    ("MACROSCOPIA", "ENCAMINHAMENTO"): ["RECEPCAO"],
    ("MICROSCOPIA", "ENCAMINHAMENTO"): ["RECEPCAO", "MACROSCOPIA", "PROCESSAMENTO", "IHQ", "REDE_EXTERNA"],
}
CG = {
    ("INICIO", "AVANCO"): ["RECEPCAO"], ("RECEPCAO", "AVANCO"): ["PROCESSAMENTO"],
    ("PROCESSAMENTO", "AVANCO"): ["MICROSCOPIA"], ("MICROSCOPIA", "AVANCO"): ["ARQUIVO"],
    ("MICROSCOPIA", "ENCAMINHAMENTO"): ["RECEPCAO", "PROCESSAMENTO", "IHQ", "REDE_EXTERNA"],  # sem MACROSCOPIA
}


class FakeAghu:
    def __init__(self, cabecalho: Optional[Dict] = None, amostras: Optional[List] = None, falha: bool = False):
        self.cabecalho = cabecalho
        self.amostras = amostras or []
        self.falha = falha

    async def buscar_solicitacao(self, numero):
        if self.falha:
            raise ConnectionError("banco fora do ar com dados sensíveis")
        return self.cabecalho

    async def listar_amostras(self, numero):
        return self.amostras


class FakeProvider:
    """Imita CasoSqliteProvider em memória (CasoProviderInterface)."""

    def __init__(self):
        self.session = object()
        self.casos: Dict[int, Dict[str, Any]] = {}
        self.amostras: List[Dict] = []
        self.movs: List[Dict] = []
        self.pendencias: Dict[int, int] = {}
        self.commits = 0
        self.sequencias: Dict[tuple, int] = {}
        self.rollbacks = 0

    async def commit(self): self.commits += 1
    async def rollback(self): self.rollbacks += 1

    async def buscar_por_solicitacao(self, numero):
        return next((c for c in self.casos.values() if c["solicitacao_aghu"] == numero), None)

    async def buscar_por_id(self, caso_id): return self.casos.get(caso_id)

    async def inserir_caso(self, d):
        caso_id = len(self.casos) + 1
        self.casos[caso_id] = {"id": caso_id, "identificador_interno": d["identificador_interno"], **{
            k: d[k] for k in ( "solicitacao_aghu", "paciente_codigo_aghu", "paciente_nome", "prontuario_aghu", "tipo_exame", "etapa_atual", "status",  "ultima_sincronizacao_aghu") if k in d}}
        return caso_id

    async def proximo_numero(self, sigla, ano):
        self.sequencias[(sigla, ano)] = self.sequencias.get((sigla, ano), 0) + 1
        return self.sequencias[(sigla, ano)]
    async def atualizar_dados_aghu(self, caso_id, nome, prontuario, agora):
        self.casos[caso_id].update(paciente_nome=nome, prontuario_aghu=prontuario, ultima_sincronizacao_aghu=agora)
    async def inserir_amostra(self, caso_id, amostra, desc): self.amostras.append({"caso_id": caso_id, "amostra_aghu": amostra})
    async def listar_amostras(self, caso_id): return [a for a in self.amostras if a["caso_id"] == caso_id]

    async def inserir_movimentacao(self, d): self.movs.append({"id": len(self.movs) + 1, **d})
    async def listar_movimentacoes(self, caso_id): return [m for m in self.movs if m["caso_id"] == caso_id]

    async def ultima_movimentacao_desvio(self, caso_id):
        desvios = [m for m in self.movs if m["caso_id"] == caso_id and m["tipo"] in ("ENCAMINHAMENTO", "RETORNO")]
        return desvios[-1] if desvios else None

    async def atualizar_etapa(self, caso_id, etapa, status, agora):
        self.casos[caso_id].update(etapa_atual=etapa, status=status)

    async def contar_pendencias_abertas(self, caso_id): return self.pendencias.get(caso_id, 0)

    async def destinos(self, tipo_exame, etapa, tipo):
        fluxo = HP if tipo_exame == "HP" else CG
        return list(fluxo.get((etapa, tipo), []))

    async def etapa_inicial(self, tipo_exame):
        return "RECEPCAO" if tipo_exame in ("HP", "CG") else None

    async def listar_casos(self, filtros, limite, deslocamento):
        itens = [c for c in self.casos.values() if not filtros.get("etapa") or c["etapa_atual"] == filtros["etapa"]]
        return itens[deslocamento: deslocamento + limite]

    async def contar_casos(self, filtros):
        return len(await self.listar_casos(filtros, 1000, 0))

    # MVP: retirada da recepção e formulários por fase
    async def marcar_retirada(self, caso_id, etapa, status, usuario, agora):
        self.casos[caso_id].update(etapa_atual=etapa, status=status, retirado_em=agora, retirado_por=usuario)

    async def desfazer_retirada(self, caso_id, status, agora):
        self.casos[caso_id].update(etapa_atual="RECEPCAO", status=status, retirado_em=None, retirado_por=None)

    async def buscar_fase(self, caso_id, etapa):
        return None


def _aghu_ok():
    return FakeAghu(
        {"solicitacao_aghu": 123, "paciente_codigo_aghu": 9, "paciente_nome": "Maria da Silva", "prontuario_aghu": 55, "tipo_exame": "HP"},
        [{"amostra_aghu": 1, "descricao": "BIOPSIA"}, {"amostra_aghu": 2, "descricao": "PECA"}],
    )


@pytest.fixture(autouse=True)
def auditoria(monkeypatch):
    registros: List[Dict] = []

    async def fake(**kwargs):
        registros.append(kwargs)

    monkeypatch.setattr(ctrl, "registrar_auditoria", fake)
    return registros


async def _status(coro) -> int:
    try:
        await coro
    except HTTPException as exc:
        return exc.status_code
    raise AssertionError("era esperado HTTPException")


async def _abrir(provider, tipo="HP", numero="123"):
    return await ctrl.abrir_caso(numero, RECEPCAO, "10.0.0.1", provider, FakeAghu({**_aghu_ok().cabecalho, "tipo_exame": tipo}, _aghu_ok().amostras))


# --- UC002 ------------------------------------------------------------------
async def test_abrir_caso_cria_vinculos_movimentacao_e_auditoria(auditoria):
    p = FakeProvider()
    caso = await _abrir(p)
    assert caso["identificador_interno"] == f"HP-0001/{ctrl._ano_local() % 100:02d}"
    assert caso["etapa_atual"] == "RECEPCAO" and caso["status"] == "EM_ANDAMENTO"
    assert len(caso["amostras"]) == 2  # nenhuma amostra sem caso
    assert p.movs[0]["tipo"] == "ABERTURA" and p.commits == 1
    assert auditoria[0]["acao"] == "ABRIR_CASO" and auditoria[0]["ip_origem"] == "10.0.0.1"
    assert auditoria[0]["categoria"] == "NEGOCIO_CLINICO"


async def test_abrir_caso_bloqueia_duplicidade():
    p = FakeProvider()
    await _abrir(p)
    assert await _status(_abrir(p)) == 409


async def test_abrir_caso_aghu_indisponivel_nao_cria_registro_parcial():
    p = FakeProvider()
    codigo = await _status(ctrl.abrir_caso("123", RECEPCAO, None, p, FakeAghu(falha=True)))
    assert codigo == 503 and not p.casos and p.commits == 0


async def test_abrir_caso_solicitacao_inexistente_e_sem_amostra():
    p = FakeProvider()
    assert await _status(ctrl.abrir_caso("123", RECEPCAO, None, p, FakeAghu(None))) == 404
    sem_amostra = FakeAghu({"solicitacao_aghu": 1, "paciente_codigo_aghu": 1, "paciente_nome": "X"}, [])
    assert await _status(ctrl.abrir_caso("123", RECEPCAO, None, p, sem_amostra)) == 422


async def test_abrir_caso_validacoes_e_perfil():
    p = FakeProvider()
    assert await _status(ctrl.abrir_caso("abc", RECEPCAO, None, p, _aghu_ok())) == 422
    assert await _status(ctrl.abrir_caso("123", RECEPCAO, None, p, FakeAghu({**_aghu_ok().cabecalho, "tipo_exame": "XX"}, _aghu_ok().amostras))) == 409
    assert await _status(ctrl.abrir_caso("123", LAB, None, p, _aghu_ok())) == 403
    assert await _status(ctrl.abrir_caso("123", RECEPCAO, None, p, FakeAghu({**_aghu_ok().cabecalho, "tipo_exame": "CO"}, _aghu_ok().amostras))) == 409  # fluxo não configurado


# --- UC017 ------------------------------------------------------------------
async def test_concluir_etapa_avanca_conforme_fluxo_e_respeita_alcada(auditoria):
    p = FakeProvider()
    await _abrir(p)
    assert await _status(ctrl.concluir_etapa(1, LAB, None, p)) == 403  # Recepção é alçada da Recepção
    caso = await ctrl.concluir_etapa(1, RECEPCAO, None, p)
    assert caso["etapa_atual"] == "MACROSCOPIA" and caso["retirado_em"]
    assert p.movs[-1]["tipo"] == "RETIRADA"  # concluir a Recepção = material retirado
    assert auditoria[-1]["dados_anteriores"]["etapa_atual"] == "RECEPCAO"


async def test_concluir_etapa_bloqueada_com_pendencia_aberta():
    p = FakeProvider()
    await _abrir(p)
    p.pendencias[1] = 1
    assert await _status(ctrl.concluir_etapa(1, RECEPCAO, None, p)) == 409
    assert p.casos[1]["etapa_atual"] == "RECEPCAO"


async def test_status_derivado_arquivado_e_nao_avanca_depois():
    p = FakeProvider()
    await _abrir(p)
    await ctrl.concluir_etapa(1, RECEPCAO, None, p)
    assert await _status(ctrl.concluir_etapa(1, LAB, None, p)) == 403  # Macroscopia é dos Residentes
    await ctrl.concluir_etapa(1, RESIDENTE, None, p)
    await ctrl.concluir_etapa(1, LAB, None, p)  # PROCESSAMENTO -> MICROSCOPIA
    caso = await ctrl.concluir_etapa(1, RESIDENTE, None, p)
    assert caso["etapa_atual"] == "ARQUIVO" and caso["status"] == "ARQUIVADO"
    assert await _status(ctrl.concluir_etapa(1, RESIDENTE, None, p)) == 409


# --- UC012 ------------------------------------------------------------------
async def _levar_a_microscopia(p, tipo="HP"):
    await _abrir(p, tipo)
    await ctrl.concluir_etapa(1, RECEPCAO, None, p)
    if tipo == "HP":
        await ctrl.concluir_etapa(1, RESIDENTE, None, p)  # MACROSCOPIA (Residentes)
    await ctrl.concluir_etapa(1, LAB, None, p)  # PROCESSAMENTO


async def test_encaminhar_exige_motivo_e_destino_valido():
    p = FakeProvider()
    await _levar_a_microscopia(p)
    assert await _status(ctrl.encaminhar_caso(1, "MACROSCOPIA", "  ", RESIDENTE, None, p)) == 422
    assert await _status(ctrl.encaminhar_caso(1, "ARQUIVO", "x", RESIDENTE, None, p)) == 409
    assert await _status(ctrl.encaminhar_caso(1, "MACROSCOPIA", "revisar", LAB, None, p)) == 403


async def test_revisao_da_peca_e_somente_hp():
    p = FakeProvider()
    await _levar_a_microscopia(p, "CG")
    assert await _status(ctrl.encaminhar_caso(1, "MACROSCOPIA", "revisar", RESIDENTE, None, p)) == 409
    caso = await ctrl.encaminhar_caso(1, "PROCESSAMENTO", "coloração especial", RESIDENTE, None, p)
    assert caso["etapa_atual"] == "PROCESSAMENTO"


async def test_encaminhar_e_retornar_preserva_historico(auditoria):
    p = FakeProvider()
    await _levar_a_microscopia(p)
    caso = await ctrl.encaminhar_caso(1, "RECEPCAO", "erro de cadastro", RESIDENTE, None, p)
    assert caso["etapa_atual"] == "RECEPCAO" and caso["acoes"]["pode_retornar"] is False  # visão do residente
    assert await _status(ctrl.concluir_etapa(1, RECEPCAO, None, p)) == 409  # em desvio: só retornar
    assert await _status(ctrl.retornar_caso(1, "", RECEPCAO, None, p)) == 422
    p.pendencias[1] = 1
    assert await _status(ctrl.retornar_caso(1, "ajustado", RECEPCAO, None, p)) == 409
    p.pendencias[1] = 0
    caso = await ctrl.retornar_caso(1, "cadastro ajustado", RECEPCAO, None, p)
    assert caso["etapa_atual"] == "MICROSCOPIA"
    tipos = [m["tipo"] for m in await ctrl.historico_caso(1, p)]
    assert tipos[-2:] == ["ENCAMINHAMENTO", "RETORNO"] and tipos[0] == "ABERTURA"  # nada reiniciado/perdido
    assert [a["acao"] for a in auditoria][-2:] == ["ENCAMINHAR_CASO", "RETORNAR_CASO"]
    assert await _status(ctrl.retornar_caso(1, "de novo", RESIDENTE, None, p)) == 409  # nada a retornar


# --- UC019 / UC018 ----------------------------------------------------------
async def test_listar_casos_pagina_e_filtra():
    p = FakeProvider()
    await _abrir(p)
    r = await ctrl.listar_casos({"etapa": "recepcao", "paciente": "  "}, 0, 500, p)
    assert r["total"] == 1 and r["pagina"] == 1 and r["limite"] == 100


async def test_historico_de_caso_inexistente():
    assert await _status(ctrl.historico_caso(99, FakeProvider())) == 404

async def test_auditoria_entra_na_mesma_transacao_do_caso(auditoria):
    """O helper não pode fazer commit próprio: caso, movimentação e auditoria vão juntos."""
    provider = FakeProvider()
    caso = await _abrir(provider)
    await ctrl.concluir_etapa(caso["id"], RECEPCAO, "10.0.0.1", provider)
    assert auditoria and all(r.get("commit") is False for r in auditoria)
    assert {r["recurso"] for r in auditoria} == {f"caso:{caso['id']}"}
    assert {r["categoria"] for r in auditoria} == {"NEGOCIO_CLINICO"}


@pytest.mark.filterwarnings("ignore::pytest.PytestWarning")
def test_formato_do_identificador_interno():
    assert ctrl.formatar_identificador("HP", 1, 2026) == "HP-0001/26"
    assert ctrl.formatar_identificador("CCV", 42, 2027) == "CCV-0042/27"
    assert ctrl.formatar_identificador("CO", 12345, 2030) == "CO-12345/30"  # passa de 9999 sem cortar


async def test_numeracao_separada_por_sigla_e_reiniciada_a_cada_ano(monkeypatch):
    p = FakeProvider()
    monkeypatch.setattr(ctrl, "_ano_local", lambda: 2026)
    ids = [(await _abrir(p, tipo, str(n)))["identificador_interno"]
           for n, tipo in enumerate(["HP", "CG", "HP", "CG", "HP"], start=1)]
    assert ids == ["HP-0001/26", "CG-0001/26", "HP-0002/26", "CG-0002/26", "HP-0003/26"]
    monkeypatch.setattr(ctrl, "_ano_local", lambda: 2027)
    assert (await _abrir(p, "HP", "99"))["identificador_interno"] == "HP-0001/27"
