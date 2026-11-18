"""Matriz de perfis do SAP pela API (T1.1).

A matriz abaixo é a mesma combinada com a equipe (plano da equipe, seção 2) e escrita à mão
de propósito: ela NÃO é lida de `src/helpers/formularios_fase.py`. Assim, mudar uma
permissão no código sem mudar esta tabela (e a combinada com a equipe) quebra o teste.

Para cada ação e cada perfil, o teste prepara uma solicitação no estado certo e confere:
* perfil da matriz → 200 (a ação funciona de verdade para ele);
* qualquer outro perfil → 403.

Também confere a regra "vê tudo, edita só o seu": todos os perfis abrem filas e formulários,
e as flags `pode_salvar` / `pode_concluir` / `editavel` seguem a mesma matriz.
"""
import sqlite3
from datetime import datetime, timezone
from itertools import count
from typing import Any, Dict, List, Optional

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from src.auth.auth import auth_handler
from src.controllers import caso_controller
from src.dependencies import get_aghu_solicitacao_provider
from src.helpers.formularios_fase import campos_da_fase
from src.main import app
from src.providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface

RECEPCAO, LABORATORIO, RESIDENTE, PRECEPTORIA, CHEFIA = (
    "RECEPCAO", "LABORATORIO", "RESIDENTE", "PRECEPTORIA", "CHEFIA",
)
PERFIS = (RECEPCAO, LABORATORIO, RESIDENTE, PRECEPTORIA, CHEFIA)

# ---------------------------------------------------------------------------
# Matriz combinada com a equipe. Mudou uma permissão? Mude aqui E no plano da equipe.
# ---------------------------------------------------------------------------
MATRIZ_SOLICITACOES: Dict[str, set] = {
    "retirar": {RECEPCAO},
    "desfazer_retirada": {RECEPCAO},
}

MATRIZ_FASES: Dict[str, Dict[str, set]] = {
    "MACROSCOPIA": {"salvar": {RESIDENTE}, "concluir": {RESIDENTE}},
    "CONGELACAO": {"salvar": {RESIDENTE, PRECEPTORIA}, "concluir": {PRECEPTORIA}},
    "PROCESSAMENTO": {"salvar": {LABORATORIO}, "concluir": {LABORATORIO}},
    "IHQ": {"salvar": {LABORATORIO}, "concluir": {LABORATORIO}},
    "MICROSCOPIA": {"salvar": {RESIDENTE, PRECEPTORIA}, "concluir": {PRECEPTORIA}},
    "REVISAO": {"salvar": {RESIDENTE, PRECEPTORIA}, "concluir": {PRECEPTORIA}},
}

#: Campos que só um perfil preenche dentro de uma fase que outros também editam.
CAMPOS_RESTRITOS: Dict[str, Dict[str, set]] = {
    "MICROSCOPIA": {"diagnostico": {PRECEPTORIA}},
    "REVISAO": {"diagnostico": {PRECEPTORIA}},
}

#: Configurações (gestão de usuários): só a Chefia.
MATRIZ_CONFIGURACOES: set = {CHEFIA}

# Tipo de exame usado para chegar a cada fase (o fluxo de cada tipo está em fluxo_transicoes).
TIPO_POR_FASE = {
    "MACROSCOPIA": "HP", "CONGELACAO": "CO", "PROCESSAMENTO": "HP",
    "IHQ": "IHQ", "MICROSCOPIA": "HP", "REVISAO": "RL",
}

USUARIOS = {
    RECEPCAO: "ana.recepcao", LABORATORIO: "bia.lab", RESIDENTE: "caio.res",
    PRECEPTORIA: "dora.pat", CHEFIA: "eva.chefia",
}


def _cabecalho(perfil: str) -> Dict[str, str]:
    """Token de acesso do usuário fictício daquele perfil."""
    token = auth_handler.create_access_token({"username": USUARIOS[perfil], "role": perfil, "groups": ["Users"]})
    return {"Authorization": f"Bearer {token}"}


class AghuFalso(AghuSolicitacaoProviderInterface):
    """AGHU simulado: qualquer número existe, com o tipo de exame registrado pelo teste."""

    def __init__(self) -> None:
        """Começa sem solicitações registradas."""
        self.tipos: Dict[str, str] = {}

    async def buscar_solicitacao(self, solicitacao_aghu: str) -> Optional[Dict[str, Any]]:
        """Cabeçalho fictício da solicitação."""
        tipo = self.tipos.get(solicitacao_aghu)
        if not tipo:
            return None
        return {
            "solicitacao_aghu": int(solicitacao_aghu), "paciente_codigo_aghu": 1, "tipo_exame": tipo,
            "prontuario_aghu": f"9{solicitacao_aghu}", "paciente_nome": "PACIENTE FICTICIO",
        }

    async def listar_amostras(self, solicitacao_aghu: str) -> List[Dict[str, Any]]:
        """Uma amostra fictícia."""
        return [{"amostra_aghu": 1, "descricao": "Amostra fictícia"}]


class Cenario:
    """Cria solicitações fictícias e as coloca no estado que cada ação exige."""

    def __init__(self, client: TestClient, db: str, aghu: AghuFalso) -> None:
        """Guarda o cliente da API, o caminho do banco e o AGHU simulado."""
        self.client, self.db, self.aghu = client, db, aghu
        self._numeros = count(500001)

    def nova(self, tipo: str) -> int:
        """Solicitação recebida no AGHU e aberta no SAP (fica em RECEPCAO, não retirada)."""
        numero = str(next(self._numeros))
        self.aghu.tipos[numero] = tipo
        r = self.client.post("/api/casos", json={"solicitacao_aghu": numero}, headers=_cabecalho(RECEPCAO))
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def na_fase(self, etapa: str) -> int:
        """Solicitação já retirada e pendente em `etapa`.

        A posição é gravada direto no banco para não depender das próprias permissões
        que este teste confere.
        """
        caso_id = self.nova(TIPO_POR_FASE[etapa])
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE casos SET etapa_atual = ?, retirado_em = ?, retirado_por = ? WHERE id = ?",
                (etapa, datetime.now(timezone.utc).isoformat(), "preparo.teste", caso_id),
            )
        return caso_id


def _valor_ficticio(campo: Dict[str, Any]) -> Any:
    """Valor válido para qualquer tipo de campo do formulário."""
    return {
        "numero": 1,
        "sim_nao": True,
        "opcao": (campo.get("opcoes") or [None])[0],
    }.get(campo["tipo"], "Texto fictício")


def _formulario_completo(etapa: str, perfil: str) -> Dict[str, Any]:
    """Todos os campos da fase que o perfil pode preencher, com valores fictícios."""
    restritos = CAMPOS_RESTRITOS.get(etapa, {})
    return {
        c["nome"]: _valor_ficticio(c)
        for c in campos_da_fase(etapa, TIPO_POR_FASE[etapa])
        if perfil in restritos.get(c["nome"], {perfil})
    }


@pytest.fixture
def cenario(tmp_path, monkeypatch):
    """Banco migrado, um usuário ativo por perfil e AGHU simulado."""
    db = tmp_path / "app.db"
    monkeypatch.setenv("SQLITE_DSN", f"sqlite+aiosqlite:///{db}")
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(caso_controller, "_ano_local", lambda: 2026)
    aghu = AghuFalso()
    app.dependency_overrides[get_aghu_solicitacao_provider] = lambda: aghu
    try:
        with TestClient(app) as client:
            with sqlite3.connect(db) as conn:
                for perfil, user in USUARIOS.items():
                    conn.execute(
                        "INSERT INTO authorized_users (username, role, active, created_at) VALUES (?, ?, 1, ?)",
                        (user, perfil, datetime.now(timezone.utc).isoformat()),
                    )
            yield Cenario(client, str(db), aghu)
    finally:
        app.dependency_overrides.pop(get_aghu_solicitacao_provider, None)


def _conferir(acao: str, respostas: Dict[str, int], permitidos: set) -> None:
    """Perfis permitidos recebem 200; os demais, 403. A mensagem mostra a matriz que a API aplicou."""
    esperado = {p: (200 if p in permitidos else 403) for p in PERFIS}
    assert respostas == esperado, (
        f"Matriz de perfis divergente em '{acao}'.\n  Esperado: {esperado}\n  API:      {respostas}\n"
        "Se a mudança foi combinada com a equipe, atualize a matriz deste teste e o plano da equipe."
    )


# ---------------------------------------------------------------------------
# Solicitações de Exames: retirar e desfazer retirada
# ---------------------------------------------------------------------------
def test_retirar(cenario):
    respostas = {}
    for perfil in PERFIS:
        caso_id = cenario.nova("HP")
        r = cenario.client.post(f"/api/solicitacoes/{caso_id}/retirar", headers=_cabecalho(perfil))
        respostas[perfil] = r.status_code
    _conferir("retirar", respostas, MATRIZ_SOLICITACOES["retirar"])


def test_desfazer_retirada(cenario):
    respostas = {}
    for perfil in PERFIS:
        caso_id = cenario.na_fase("MACROSCOPIA")
        r = cenario.client.post(f"/api/solicitacoes/{caso_id}/desfazer-retirada", headers=_cabecalho(perfil))
        respostas[perfil] = r.status_code
    _conferir("desfazer retirada", respostas, MATRIZ_SOLICITACOES["desfazer_retirada"])


# ---------------------------------------------------------------------------
# Fases: salvar e concluir
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("etapa", list(MATRIZ_FASES))
def test_salvar_na_fase(cenario, etapa):
    respostas = {}
    for perfil in PERFIS:
        caso_id = cenario.na_fase(etapa)
        r = cenario.client.put(
            f"/api/fases/{etapa}/solicitacoes/{caso_id}",
            json={"dados": {"observacoes": f"rascunho de {perfil}"}}, headers=_cabecalho(perfil),
        )
        respostas[perfil] = r.status_code
    _conferir(f"salvar {etapa}", respostas, MATRIZ_FASES[etapa]["salvar"])


@pytest.mark.parametrize("etapa", list(MATRIZ_FASES))
def test_concluir_na_fase(cenario, etapa):
    respostas = {}
    for perfil in PERFIS:
        caso_id = cenario.na_fase(etapa)
        r = cenario.client.post(
            f"/api/fases/{etapa}/solicitacoes/{caso_id}/concluir",
            json={"dados": _formulario_completo(etapa, perfil)}, headers=_cabecalho(perfil),
        )
        respostas[perfil] = r.status_code
        if r.status_code == 200:
            assert r.json()["situacao"] == "CONCLUIDA" and r.json()["solicitacao"]["etapa_atual"] != etapa
    _conferir(f"concluir {etapa}", respostas, MATRIZ_FASES[etapa]["concluir"])


# ---------------------------------------------------------------------------
# "Vê tudo, edita só o seu"
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("etapa", list(MATRIZ_FASES))
def test_todos_veem_e_flags_seguem_a_matriz(cenario, etapa):
    caso_id = cenario.na_fase(etapa)
    restritos = CAMPOS_RESTRITOS.get(etapa, {})
    for perfil in PERFIS:
        cab = _cabecalho(perfil)
        fila = cenario.client.get(f"/api/fases/{etapa}/fila", headers=cab)
        assert fila.status_code == 200, f"{perfil} não conseguiu ver a fila de {etapa}"
        assert caso_id in [i["id"] for i in fila.json()["items"]]

        form = cenario.client.get(f"/api/fases/{etapa}/solicitacoes/{caso_id}", headers=cab)
        assert form.status_code == 200, f"{perfil} não conseguiu abrir o formulário de {etapa}"
        corpo = form.json()
        pode_salvar = perfil in MATRIZ_FASES[etapa]["salvar"]
        assert corpo["pode_salvar"] is pode_salvar, f"pode_salvar errado para {perfil} em {etapa}"
        assert corpo["pode_concluir"] is (perfil in MATRIZ_FASES[etapa]["concluir"]), (
            f"pode_concluir errado para {perfil} em {etapa}"
        )
        for campo in corpo["campos"]:
            esperado = pode_salvar and perfil in restritos.get(campo["nome"], {perfil})
            assert campo["editavel"] is esperado, f"campo '{campo['nome']}' de {etapa} com editavel errado para {perfil}"


def test_todos_veem_as_solicitacoes(cenario):
    cenario.nova("HP")
    for perfil in PERFIS:
        for situacao in ("NAO_RETIRADO", "RETIRADO"):
            r = cenario.client.get("/api/solicitacoes", params={"situacao": situacao}, headers=_cabecalho(perfil))
            assert r.status_code == 200, f"{perfil} não conseguiu ver {situacao}"


@pytest.mark.parametrize("etapa", sorted(CAMPOS_RESTRITOS))
def test_campo_restrito_e_ignorado_para_outro_perfil(cenario, etapa):
    """O residente pode salvar a fase, mas o diagnóstico enviado por ele não é gravado."""
    caso_id = cenario.na_fase(etapa)
    r = cenario.client.put(
        f"/api/fases/{etapa}/solicitacoes/{caso_id}",
        json={"dados": {"diagnostico": "tentativa do residente"}}, headers=_cabecalho(RESIDENTE),
    )
    assert r.status_code == 200, r.text
    assert r.json()["dados"].get("diagnostico") is None


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
def test_configuracoes_so_chefia(cenario):
    respostas = {
        perfil: cenario.client.get("/api/admin/usuarios", headers=_cabecalho(perfil)).status_code
        for perfil in PERFIS
    }
    _conferir("Configurações (usuários)", respostas, MATRIZ_CONFIGURACOES)


def test_sem_login_nada_responde(cenario):
    caso_id = cenario.na_fase("MACROSCOPIA")
    assert cenario.client.get("/api/solicitacoes").status_code == 401
    assert cenario.client.get(f"/api/fases/MACROSCOPIA/solicitacoes/{caso_id}").status_code == 401
    assert cenario.client.post(f"/api/solicitacoes/{caso_id}/desfazer-retirada").status_code == 401
