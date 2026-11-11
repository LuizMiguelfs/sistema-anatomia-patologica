"""Controller das fases do setor (MVP): fila de trabalho e formulário de cada fase.

Regras (decididas com a equipe):
* A fila mostra só as solicitações que estão naquela fase agora; urgentes no topo e, abaixo,
  da entrada mais antiga para a mais recente.
* Concluídas continuam na mesma lista por DIAS_EDICAO_APOS_CONCLUSAO dias, para edição.
* "Salvar" grava o formulário sem exigir obrigatórios. "Concluído" exige os obrigatórios e
  envia a solicitação para a próxima fase (ou de volta à fase de origem, se ela veio por
  encaminhamento, como a IHQ pedida na Microscopia).
* Só o perfil responsável edita; os demais visualizam. Tudo fica auditado (RN-04).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..helpers.formularios_fase import (
    DIAS_EDICAO_APOS_CONCLUSAO, FASES, FASES_POR_ETAPA, campos_da_fase,
)
from ..providers.interfaces.caso_provider_interface import CasoProviderInterface
from .caso_controller import (
    STATUS_ARQUIVADO, _agora, _caso_ou_404, _esta_em_desvio, _exigir_sem_pendencias, _gravar,
    _login, _perfil, _status_derivado,
)
from .solicitacao_controller import normalizar_filtros_busca

logger = logging.getLogger("fases")

SITUACAO_RASCUNHO = "RASCUNHO"
SITUACAO_CONCLUIDA = "CONCLUIDA"
_MAX_TEXTO = 4000
_MAX_NUMERO = 10000


def _fase_ou_404(etapa: str) -> Dict[str, Any]:
    """Definição da fase pela etapa, ou 404."""
    fase = FASES_POR_ETAPA.get((etapa or "").strip().upper())
    if not fase:
        raise HTTPException(status_code=404, detail="Fase não encontrada.")
    return fase


def _limite_edicao() -> datetime:
    """Concluídas a partir deste instante (UTC) ainda podem ser editadas na fila."""
    return datetime.now(timezone.utc) - timedelta(days=DIAS_EDICAO_APOS_CONCLUSAO)


def _editavel_ate(concluido_em: Optional[str]) -> Optional[str]:
    """Data/hora (UTC) até quando a fase concluída aceita edição."""
    if not concluido_em:
        return None
    return (datetime.fromisoformat(concluido_em) + timedelta(days=DIAS_EDICAO_APOS_CONCLUSAO)).isoformat()


def _dentro_do_prazo(concluido_em: Optional[str]) -> bool:
    """True se a conclusão foi há menos de DIAS_EDICAO_APOS_CONCLUSAO dias."""
    return bool(concluido_em) and datetime.fromisoformat(concluido_em) >= _limite_edicao()


def _pode_editar_campo(campo: Dict[str, Any], perfil: str) -> bool:
    """Campos com `perfis` só são editados por esses perfis (ex.: diagnóstico pelo patologista)."""
    return perfil in campo.get("perfis", [perfil])


def formularios() -> List[Dict[str, Any]]:
    """Definições das fases e dos campos (provisórias até a reunião com o setor)."""
    return [
        {**f, "dias_edicao_apos_conclusao": DIAS_EDICAO_APOS_CONCLUSAO} for f in FASES
    ]


# --------------------------------------------------------------------------- #
# Fila da fase                                                                 #
# --------------------------------------------------------------------------- #
async def listar_fila(
    etapa: str, filtros: Dict[str, Any], pagina: int, limite: int, provider: CasoProviderInterface,
) -> Dict[str, Any]:
    """Pendentes da fase e concluídas recentes (ainda editáveis), paginadas."""
    fase = _fase_ou_404(etapa)
    pagina = max(pagina, 1)
    limite = min(max(limite, 1), 100)
    limpos = normalizar_filtros_busca(filtros)
    desde = _limite_edicao().isoformat()
    itens = await provider.listar_fila(fase["etapa"], limpos, desde, limite, (pagina - 1) * limite)
    total = await provider.contar_fila(fase["etapa"], limpos, desde)
    return {
        "items": [
            {**i, "urgente": bool(i.get("urgente")), "pendente": bool(i.get("pendente")),
             "editavel_ate": None if i.get("pendente") else _editavel_ate(i.get("concluido_em"))}
            for i in itens
        ],
        "total": total, "pagina": pagina, "limite": limite,
    }


# --------------------------------------------------------------------------- #
# Formulário da fase                                                           #
# --------------------------------------------------------------------------- #
def _normalizar_valor(campo: Dict[str, Any], valor: Any) -> Any:
    """Valida e normaliza o valor conforme o tipo do campo; vazio vira None."""
    rotulo = campo["rotulo"]
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    tipo = campo["tipo"]
    if tipo in ("texto", "texto_longo"):
        if not isinstance(valor, (str, int, float)):
            raise HTTPException(status_code=422, detail=f"Valor inválido em '{rotulo}'.")
        texto = str(valor).strip()
        if len(texto) > _MAX_TEXTO:
            raise HTTPException(status_code=422, detail=f"'{rotulo}' passa de {_MAX_TEXTO} caracteres.")
        return texto
    if tipo == "numero":
        try:
            numero = int(str(valor).strip())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"'{rotulo}' deve ser um número inteiro.")
        if not 0 <= numero <= _MAX_NUMERO:
            raise HTTPException(status_code=422, detail=f"'{rotulo}' deve estar entre 0 e {_MAX_NUMERO}.")
        return numero
    if tipo == "sim_nao":
        if not isinstance(valor, bool):
            raise HTTPException(status_code=422, detail=f"'{rotulo}' deve ser sim ou não.")
        return valor
    if tipo == "opcao":
        if valor not in campo.get("opcoes", []):
            raise HTTPException(status_code=422, detail=f"Opção inválida em '{rotulo}'.")
        return valor
    raise HTTPException(status_code=422, detail=f"Tipo de campo desconhecido em '{rotulo}'.")


def _mesclar(
    campos: List[Dict[str, Any]], anteriores: Dict[str, Any], enviados: Dict[str, Any], perfil: str,
) -> Dict[str, Any]:
    """Aplica só os campos que o perfil pode editar; os demais mantêm o valor gravado."""
    por_nome = {c["nome"]: c for c in campos}
    desconhecidos = sorted(set(enviados) - set(por_nome))
    if desconhecidos:
        raise HTTPException(status_code=422, detail=f"Campo(s) não previsto(s) neste formulário: {', '.join(desconhecidos)}.")
    resultado: Dict[str, Any] = {}
    for campo in campos:
        nome = campo["nome"]
        if nome in enviados and _pode_editar_campo(campo, perfil):
            resultado[nome] = _normalizar_valor(campo, enviados[nome])
        else:
            resultado[nome] = anteriores.get(nome)
    return resultado


def campos_faltando(campos: List[Dict[str, Any]], dados: Dict[str, Any]) -> List[str]:
    """Rótulos dos campos obrigatórios ainda vazios."""
    return [c["rotulo"] for c in campos if c.get("obrigatorio") and dados.get(c["nome"]) in (None, "")]


def _exigir_obrigatorios(campos: List[Dict[str, Any]], dados: Dict[str, Any]) -> None:
    """422 listando os campos obrigatórios que faltam."""
    faltando = campos_faltando(campos, dados)
    if faltando:
        raise HTTPException(status_code=422, detail=f"Preencha os campos obrigatórios: {', '.join(faltando)}.")


async def obter_fase(
    etapa: str, caso_id: int, usuario: Dict[str, Any], provider: CasoProviderInterface,
) -> Dict[str, Any]:
    """Formulário da fase para a solicitação, com o que o perfil pode fazer nele."""
    fase = _fase_ou_404(etapa)
    caso = await _caso_ou_404(provider, caso_id)
    registro = await provider.buscar_fase(caso_id, fase["etapa"])
    perfil = _perfil(usuario)
    pendente = caso["etapa_atual"] == fase["etapa"] and caso["status"] != STATUS_ARQUIVADO
    concluida_editavel = bool(
        registro and registro["situacao"] == SITUACAO_CONCLUIDA and not pendente
        and _dentro_do_prazo(registro.get("concluido_em"))
    )
    campos = campos_da_fase(fase["etapa"], caso["tipo_exame"])
    pode_salvar = perfil in fase["salvar"] and (pendente or concluida_editavel)
    amostras = await provider.listar_amostras(caso_id)
    return {
        "etapa": fase["etapa"], "rotulo": fase["rotulo"],
        "solicitacao": {
            "id": caso["id"], "identificador_interno": caso["identificador_interno"],
            "solicitacao_aghu": caso["solicitacao_aghu"], "paciente_nome": caso["paciente_nome"],
            "prontuario_aghu": caso.get("prontuario_aghu"), "tipo_exame": caso["tipo_exame"],
            "etapa_atual": caso["etapa_atual"], "urgente": bool(caso.get("urgente")),
            "amostras": amostras,
        },
        "situacao": registro["situacao"] if registro else None,
        "dados": registro["dados"] if registro else {},
        "salvo_por": registro["salvo_por"] if registro else None,
        "salvo_em": registro["salvo_em"] if registro else None,
        "concluido_por": registro["concluido_por"] if registro else None,
        "concluido_em": registro["concluido_em"] if registro else None,
        "editavel_ate": _editavel_ate(registro.get("concluido_em")) if concluida_editavel else None,
        "pendente": pendente,
        "pode_salvar": pode_salvar,
        "pode_concluir": perfil in fase["concluir"] and pendente,
        "campos": [{**c, "editavel": pode_salvar and _pode_editar_campo(c, perfil)} for c in campos],
    }


async def salvar_fase(
    etapa: str, caso_id: int, enviados: Dict[str, Any], usuario: Dict[str, Any], ip: Optional[str],
    provider: CasoProviderInterface,
) -> Dict[str, Any]:
    """Salvar: grava o formulário (rascunho na fase atual, ou edição de fase concluída dentro do prazo)."""
    fase = _fase_ou_404(etapa)
    perfil = _perfil(usuario)
    if perfil not in fase["salvar"]:
        raise HTTPException(status_code=403, detail=f"Seu perfil não tem permissão para editar a fase {fase['rotulo']}.")
    caso = await _caso_ou_404(provider, caso_id)
    registro = await provider.buscar_fase(caso_id, fase["etapa"])
    pendente = caso["etapa_atual"] == fase["etapa"] and caso["status"] != STATUS_ARQUIVADO
    editando_concluida = bool(
        registro and registro["situacao"] == SITUACAO_CONCLUIDA and not pendente
        and _dentro_do_prazo(registro.get("concluido_em"))
    )
    if not (pendente or editando_concluida):
        raise HTTPException(status_code=409, detail=f"A solicitação não está na fase {fase['rotulo']} e não pode mais ser editada nela.")

    campos = campos_da_fase(fase["etapa"], caso["tipo_exame"])
    anteriores = registro["dados"] if registro else {}
    dados = _mesclar(campos, anteriores, enviados, perfil)
    if editando_concluida:
        _exigir_obrigatorios(campos, dados)  # uma fase concluída não pode ficar incompleta
    agora = _agora()
    try:
        await provider.salvar_fase({
            "caso_id": caso_id, "etapa": fase["etapa"], "dados": dados,
            "situacao": SITUACAO_CONCLUIDA if editando_concluida else SITUACAO_RASCUNHO,
            "usuario": _login(usuario), "agora": agora,
            "concluido_por": registro["concluido_por"] if editando_concluida else None,
            "concluido_em": registro["concluido_em"] if editando_concluida else None,
        })
        await _gravar(
            provider, usuario=usuario, ip=ip,
            acao=f"{'EDITAR_CONCLUIDA' if editando_concluida else 'SALVAR'}_{fase['etapa']}",
            caso_id=caso_id, anteriores=anteriores or None, novos=dados,
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        logger.error("Falha em %s: %s", "SALVAR_FASE", erro.__class__.__name__)
        raise
    return await obter_fase(fase["etapa"], caso_id, usuario, provider)


async def concluir_fase(
    etapa: str, caso_id: int, enviados: Dict[str, Any], usuario: Dict[str, Any], ip: Optional[str],
    provider: CasoProviderInterface,
) -> Dict[str, Any]:
    """Concluído: exige os obrigatórios e envia a solicitação para a próxima fase."""
    fase = _fase_ou_404(etapa)
    perfil = _perfil(usuario)
    if perfil not in fase["concluir"]:
        raise HTTPException(status_code=403, detail=f"Seu perfil não tem permissão para concluir a fase {fase['rotulo']}.")
    caso = await _caso_ou_404(provider, caso_id)
    if caso["etapa_atual"] != fase["etapa"] or caso["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail=f"A solicitação não está pendente na fase {fase['rotulo']}.")
    await _exigir_sem_pendencias(provider, caso_id)

    campos = campos_da_fase(fase["etapa"], caso["tipo_exame"])
    registro = await provider.buscar_fase(caso_id, fase["etapa"])
    anteriores = registro["dados"] if registro else {}
    dados = _mesclar(campos, anteriores, enviados, perfil)
    _exigir_obrigatorios(campos, dados)

    # Veio por encaminhamento (ex.: IHQ pedida na Microscopia)? Volta à fase de origem.
    desvio = await _esta_em_desvio(provider, caso)
    if desvio:
        destino, tipo_mov = desvio["etapa_origem"], "RETORNO"
    else:
        proximas = await provider.destinos(caso["tipo_exame"], fase["etapa"], "AVANCO")
        if not proximas:
            raise HTTPException(status_code=409, detail=f"Não há próxima fase configurada após {fase['rotulo']} para {caso['tipo_exame']}.")
        destino, tipo_mov = proximas[0], "CONCLUSAO"
    status = _status_derivado(destino)
    agora = _agora()
    login = _login(usuario)
    try:
        await provider.salvar_fase({
            "caso_id": caso_id, "etapa": fase["etapa"], "dados": dados, "situacao": SITUACAO_CONCLUIDA,
            "usuario": login, "agora": agora, "concluido_por": login, "concluido_em": agora,
        })
        await provider.inserir_movimentacao({
            "caso_id": caso_id, "tipo": tipo_mov, "etapa_origem": fase["etapa"],
            "etapa_destino": destino, "motivo": f"Fase {fase['rotulo']} concluída", "usuario": login, "agora": agora,
        })
        await provider.atualizar_etapa(caso_id, destino, status, agora)
        await _gravar(
            provider, usuario=usuario, ip=ip, acao=f"CONCLUIR_{fase['etapa']}", caso_id=caso_id,
            anteriores={"etapa_atual": fase["etapa"], "formulario": anteriores or None},
            novos={"etapa_atual": destino, "status": status, "formulario": dados},
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        logger.error("Falha em %s: %s", "CONCLUIR_FASE", erro.__class__.__name__)
        raise
    return await obter_fase(fase["etapa"], caso_id, usuario, provider)
