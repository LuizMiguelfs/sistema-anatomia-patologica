# tests/test_auditoria.py
"""
Consulta da trilha de auditoria: rota administrativa (/api/admin/auditoria, TI ou Chefia)
e histórico de um recurso (/api/auditoria/historico, qualquer usuário autenticado).
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from tests.auditoria_helpers import _admin, _gravar, _h, _token, ambiente  # noqa: F401


# -------------------------------------------------------- consulta administrativa
def test_consulta_exige_autenticacao(ambiente):
    client, _ = ambiente
    assert client.get("/api/admin/auditoria").status_code == 401


def test_consulta_negada_sem_grupo_ti_nem_chefia(ambiente):
    client, _ = ambiente
    r = client.get("/api/admin/auditoria", headers=_h(_token(["Users"])))
    assert r.status_code == 403


def test_consulta_permitida_ao_grupo_ti(ambiente):
    client, _ = ambiente
    _gravar(client)
    r = client.get("/api/admin/auditoria", headers=_admin(client))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["total"] == 1
    item = corpo["itens"][0]
    assert item["dados_novos"] == {"nome": "MARIA"}  # JSON devolvido como objeto
    assert item["ip_origem"] == "10.0.0.1"
    assert item["created_at"].endswith(("+00:00", "Z"))


def test_consulta_permitida_ao_perfil_chefia(ambiente):
    client, _ = ambiente
    r = client.get("/api/admin/auditoria", headers=_h(_token(["Users"], role="CHEFIA")))
    assert r.status_code == 200, r.text


def test_consulta_filtros_e_ordenacao(ambiente):
    client, _ = ambiente
    _gravar(client, usuario="Joao.Silva", acao="criar_paciente", recurso="paciente:1")
    _gravar(client, usuario="maria.souza", categoria="SEGURANCA", acao="ALTERAR_PERFIL_USUARIO", recurso="usuario:x")
    _gravar(client, usuario="joao.silva", acao="ALTERAR_PACIENTE", recurso="paciente:10")
    _gravar(client, usuario="joao.silva", acao="ALTERAR_PACIENTE", recurso="paciente_x:1")
    h = _admin(client)

    def ids(**params):
        return [i["recurso"] for i in client.get("/api/admin/auditoria", params=params, headers=h).json()["itens"]]

    # Mais recente primeiro
    assert ids() == ["paciente_x:1", "paciente:10", "usuario:x", "paciente:1"]
    assert ids(usuario="JOAO.SILVA") == ["paciente_x:1", "paciente:10", "paciente:1"]
    assert ids(categoria="SEGURANCA") == ["usuario:x"]
    assert ids(acao="criar_paciente") == ["paciente:1"]
    assert ids(recurso="paciente:1") == ["paciente:1"]          # exato
    assert ids(recurso="paciente:*") == ["paciente:10", "paciente:1"]  # prefixo; '_' não é curinga
    assert ids(usuario="ninguem") == []


def test_filtro_por_data_respeita_o_fuso_de_quem_consulta(ambiente):
    """22h de 05/11 em Recife (UTC-3) é gravado como 01h de 06/11 em UTC."""
    client, db_path = ambiente
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO audit_logs (created_at, usuario, categoria, acao, recurso) "
            "VALUES ('2026-11-06 01:00:00.000000', 'joao.silva', 'NEGOCIO_CLINICO', 'NOTURNO', 'caso:1')"
        )
    h = _admin(client)

    def total(**p):
        return client.get("/api/admin/auditoria", params={"data_inicio": "2026-11-05", "data_fim": "2026-11-05", **p},
                          headers=h).json()["total"]

    assert total(utc_offset_minutos=-180) == 1  # dia 05 em Recife
    assert total() == 0                          # dia 05 em UTC
    assert client.get("/api/admin/auditoria", params={"utc_offset_minutos": 5000}, headers=h).status_code == 400


def test_consulta_paginacao(ambiente):
    client, _ = ambiente
    for i in range(5):
        _gravar(client, recurso=f"caso:{i}")
    h = _admin(client)
    r = client.get("/api/admin/auditoria", params={"limite": 2, "offset": 2}, headers=h).json()
    assert r["total"] == 5 and r["limite"] == 2 and r["offset"] == 2
    assert [i["recurso"] for i in r["itens"]] == ["caso:2", "caso:1"]


def test_consulta_filtro_por_data(ambiente):
    client, _ = ambiente
    _gravar(client)
    h = _admin(client)
    hoje = datetime.now(timezone.utc).date()
    ontem = hoje - timedelta(days=1)

    def total(**p):
        return client.get("/api/admin/auditoria", params=p, headers=h).json()["total"]

    assert total(data_inicio=hoje.isoformat(), data_fim=hoje.isoformat()) == 1
    assert total(data_fim=ontem.isoformat()) == 0
    r = client.get("/api/admin/auditoria", params={"data_inicio": hoje.isoformat(), "data_fim": ontem.isoformat()}, headers=h)
    assert r.status_code == 400 and "data inicial" in r.json()["detail"]


def test_consulta_valida_parametros(ambiente):
    client, _ = ambiente
    h = _admin(client)
    assert client.get("/api/admin/auditoria", params={"categoria": "OUTRA"}, headers=h).status_code == 400
    assert client.get("/api/admin/auditoria", params={"limite": 1000}, headers=h).status_code == 400


def test_nao_existe_rota_de_escrita_na_auditoria(ambiente):
    client, _ = ambiente
    h = _admin(client)
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(client, metodo)("/api/admin/auditoria", headers=h).status_code == 405


# ------------------------------------------------------------ histórico (RF021)
def test_historico_aberto_a_qualquer_usuario_autenticado(ambiente):
    client, _ = ambiente
    _gravar(client, recurso="caso:7", acao="REGISTRAR_RECEBIMENTO")
    _gravar(client, recurso="caso:7", acao="CONCLUIR_MACROSCOPIA")
    _gravar(client, recurso="caso:8")
    _gravar(client, recurso="caso:7", categoria="SEGURANCA", acao="EVENTO_DE_ACESSO")

    assert client.get("/api/auditoria/historico", params={"recurso": "caso:7"}).status_code == 401

    r = client.get("/api/auditoria/historico", params={"recurso": "caso:7"}, headers=_h(_token(["Users"])))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["total"] == 2  # só NEGOCIO_CLINICO, só o recurso pedido
    assert [i["acao"] for i in corpo["itens"]] == ["CONCLUIR_MACROSCOPIA", "REGISTRAR_RECEBIMENTO"]
    assert "ip_origem" not in corpo["itens"][0]


def test_historico_valida_formato_do_recurso(ambiente):
    client, _ = ambiente
    h = _h(_token(["Users"]))
    assert client.get("/api/auditoria/historico", headers=h).status_code == 400
    assert client.get("/api/auditoria/historico", params={"recurso": "semdoispontos"}, headers=h).status_code == 400


def test_historico_nao_aceita_prefixo(ambiente):
    client, _ = ambiente
    _gravar(client, recurso="caso:1")
    r = client.get("/api/auditoria/historico", params={"recurso": "caso:*"}, headers=_h(_token(["Users"])))
    assert r.status_code == 200 and r.json()["total"] == 0
