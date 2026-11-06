"""Controller do módulo de Casos (fluxo principal de negócio do SAP).

Cobre: UC002 (abrir caso), UC019 (buscar casos), UC017 (concluir etapa),
UC012 (encaminhar/retornar) e UC018 (histórico).

Regras centrais:
* O fluxo permitido por tipo de exame vem do banco (tabela ``fluxo_transicoes``),
  nunca de código (RF005 / RNF011).
* Toda mutação grava movimentação (append-only) e ``audit_logs`` na MESMA
  transação (RF021 / RNF002 / RNF006).
* Dados do AGHU são somente leitura (RNF005).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from ..helpers.audit_helper import registrar_auditoria
from ..providers.implementations.aghu_solicitacao_postgres_provider import AghuSolicitacaoPostgresProvider
from ..providers.implementations.caso_postgres_provider import CasoPostgresProvider

TIPOS_EXAME = {"HP", "CO", "CG", "CCV"}
ETAPA_ARQUIVO = "ARQUIVO"
STATUS_EM_ANDAMENTO = "EM_ANDAMENTO"
STATUS_ARQUIVADO = "ARQUIVADO"

# Perfis (RF002). Ajustar os nomes ao que o RBAC local do projeto gravar na tabela de usuários.
PERFIL_RECEPCAO = "RECEPCAO"
PERFIL_LABORATORIO = "LABORATORIO"
PERFIL_RESIDENTE = "RESIDENTE"
PERFIL_PRECEPTORIA = "PRECEPTORIA"

# Quem é "responsável" por cada etapa (alçada para concluir/encaminhar/retornar).
PERFIS_POR_ETAPA: Dict[str, set] = {
    "RECEPCAO": {PERFIL_RECEPCAO},
    "MACROSCOPIA": {PERFIL_LABORATORIO},
    "CONGELACAO": {PERFIL_LABORATORIO},
    "PROCESSAMENTO": {PERFIL_LABORATORIO},
    "IHQ": {PERFIL_LABORATORIO},
    "REDE_EXTERNA": {PERFIL_LABORATORIO},
    "MICROSCOPIA": {PERFIL_RESIDENTE, PERFIL_PRECEPTORIA},
}


# --------------------------------------------------------------------------- #
# Utilitários                                                                  #
# --------------------------------------------------------------------------- #
def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _perfil(usuario: Dict[str, Any]) -> str:
    return str(usuario.get("perfil") or usuario.get("role") or "").upper()


def _login(usuario: Dict[str, Any]) -> str:
    return str(usuario.get("username") or usuario.get("sub") or "desconhecido")


def _status_derivado(etapa: str) -> str:
    """Status derivado da etapa registrada (RF019): nunca informado pelo cliente."""
    return STATUS_ARQUIVADO if etapa == ETAPA_ARQUIVO else STATUS_EM_ANDAMENTO


def _exigir_perfil(usuario: Dict[str, Any], permitidos: set, acao: str) -> None:
    if _perfil(usuario) not in permitidos:
        raise HTTPException(status_code=403, detail=f"Seu perfil não tem permissão para {acao}.")


def _motivo_obrigatorio(motivo: Optional[str]) -> str:
    texto = (motivo or "").strip()
    if not texto:
        raise HTTPException(status_code=422, detail="O motivo é obrigatório.")
    return texto


async def _caso_ou_404(provider: CasoPostgresProvider, caso_id: int) -> Dict[str, Any]:
    caso = await provider.buscar_por_id(caso_id)
    if not caso:
        raise HTTPException(status_code=404, detail="Caso não encontrado.")
    return caso


async def _exigir_sem_pendencias(provider: CasoPostgresProvider, caso_id: int) -> None:
    if await provider.contar_pendencias_abertas(caso_id) > 0:
        raise HTTPException(
            status_code=409,
            detail="O caso possui inconformidade em aberto. Resolva-a antes de prosseguir.",
        )


async def _esta_em_desvio(provider: CasoPostgresProvider, caso: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retorna a movimentação de encaminhamento se o caso está aguardando retorno."""
    ultima = await provider.ultima_movimentacao_desvio(caso["id"])
    if ultima and ultima["tipo"] == "ENCAMINHAMENTO" and ultima["etapa_destino"] == caso["etapa_atual"]:
        return ultima
    return None


async def _gravar(
    provider: CasoPostgresProvider,
    *,
    usuario: Dict[str, Any],
    ip: Optional[str],
    acao: str,
    caso_id: int,
    anteriores: Optional[Dict[str, Any]],
    novos: Dict[str, Any],
) -> None:
    await registrar_auditoria(
        db=provider.session,
        usuario=_login(usuario),
        categoria="NEGOCIO_CLINICO",
        acao=acao,
        recurso=f"caso:{caso_id}",
        dados_anteriores=anteriores,
        dados_novos=novos,
        ip_origem=ip,
        commit=False,  # grava no commit do controller, junto com a alteração (RN-04)
    )


# --------------------------------------------------------------------------- #
# UC002 - Abrir caso a partir do AGHU                                          #
# --------------------------------------------------------------------------- #
def _validar_solicitacao(solicitacao: str) -> str:
    numero = (solicitacao or "").strip()
    if not numero.isdigit():
        raise HTTPException(status_code=422, detail="Informe um número de solicitação válido.")
    return numero


async def consultar_solicitacao_aghu(
    solicitacao: str,
    provider: CasoPostgresProvider,
    aghu: AghuSolicitacaoPostgresProvider,
) -> Dict[str, Any]:
    """Pré-visualização para a Recepção confirmar antes de criar o caso."""
    numero = _validar_solicitacao(solicitacao)
    try:
        cabecalho = await aghu.buscar_solicitacao(numero)
        amostras = await aghu.listar_amostras(numero) if cabecalho else []
    except Exception:  # não expor detalhes do banco (RNF007)
        raise HTTPException(status_code=503, detail="AGHU indisponível no momento. Tente novamente em instantes.")
    if not cabecalho:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada no AGHU.")
    existente = await provider.buscar_por_solicitacao(numero)
    return {**cabecalho, "amostras": amostras, "caso_existente": existente["identificador_interno"] if existente else None}


async def abrir_caso(
    solicitacao: str,
    tipo_exame: str,
    usuario: Dict[str, Any],
    ip: Optional[str],
    provider: CasoPostgresProvider,
    aghu: AghuSolicitacaoPostgresProvider,
) -> Dict[str, Any]:
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "abrir casos")
    numero = _validar_solicitacao(solicitacao)
    tipo = (tipo_exame or "").strip().upper()
    if tipo not in TIPOS_EXAME:
        raise HTTPException(status_code=422, detail=f"Tipo de exame inválido. Use: {', '.join(sorted(TIPOS_EXAME))}.")

    if await provider.buscar_por_solicitacao(numero):
        raise HTTPException(status_code=409, detail="Já existe um caso aberto para esta solicitação.")

    try:
        cabecalho = await aghu.buscar_solicitacao(numero)
        amostras = await aghu.listar_amostras(numero) if cabecalho else []
    except Exception:
        raise HTTPException(status_code=503, detail="AGHU indisponível no momento. Nenhum caso foi criado.")
    if not cabecalho:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada no AGHU.")
    if not amostras:
        raise HTTPException(status_code=422, detail="A solicitação não possui amostra vinculada.")

    etapa_inicial = await provider.etapa_inicial(tipo)
    if not etapa_inicial:
        raise HTTPException(status_code=409, detail=f"Fluxo do exame {tipo} não está configurado.")

    agora = _agora()
    login = _login(usuario)
    try:
        caso_id = await provider.inserir_caso(
            {
                "identificador_provisorio": f"PROV-{numero}-{agora}",
                "solicitacao_aghu": numero,
                "paciente_codigo_aghu": str(cabecalho["paciente_codigo_aghu"]),
                "paciente_nome": cabecalho["paciente_nome"],
                "prontuario_aghu": str(cabecalho.get("prontuario_aghu") or "") or None,
                "tipo_exame": tipo,
                "etapa_atual": etapa_inicial,
                "status": _status_derivado(etapa_inicial),
                "usuario": login,
                "agora": agora,
            }
        )
        identificador = f"SAP-{agora[:4]}-{caso_id:06d}"
        await provider.definir_identificador(caso_id, identificador)
        for amostra in amostras:
            await provider.inserir_amostra(caso_id, str(amostra["amostra_aghu"]), amostra.get("descricao"))
        await provider.inserir_movimentacao(
            {
                "caso_id": caso_id, "tipo": "ABERTURA", "etapa_origem": None,
                "etapa_destino": etapa_inicial, "motivo": None, "usuario": login, "agora": agora,
            }
        )
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="ABRIR_CASO", caso_id=caso_id, anteriores=None,
            novos={
                "identificador_interno": identificador, "solicitacao_aghu": numero,
                "tipo_exame": tipo, "etapa_atual": etapa_inicial, "amostras": len(amostras),
            },
        )
        await provider.commit()
    except IntegrityError:
        await provider.rollback()
        raise HTTPException(status_code=409, detail="Já existe um caso aberto para esta solicitação.")
    except Exception:
        await provider.rollback()
        raise
    return await obter_caso(caso_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC019 - Buscar casos                                                         #
# --------------------------------------------------------------------------- #
async def listar_casos(
    filtros: Dict[str, Any], pagina: int, limite: int, provider: CasoPostgresProvider
) -> Dict[str, Any]:
    pagina = max(pagina, 1)
    limite = min(max(limite, 1), 100)
    limpos = {k: (v.strip() if isinstance(v, str) else v) or None for k, v in filtros.items()}
    for chave in ("tipo_exame", "etapa", "status"):
        if limpos.get(chave):
            limpos[chave] = limpos[chave].upper()
    itens = await provider.listar_casos(limpos, limite, (pagina - 1) * limite)
    total = await provider.contar_casos(limpos)
    return {"items": itens, "total": total, "pagina": pagina, "limite": limite}


async def obter_caso(caso_id: int, usuario: Dict[str, Any], provider: CasoPostgresProvider) -> Dict[str, Any]:
    caso = await _caso_ou_404(provider, caso_id)
    amostras = await provider.listar_amostras(caso_id)
    etapa = caso["etapa_atual"]
    responsavel = _perfil(usuario) in PERFIS_POR_ETAPA.get(etapa, set())
    em_desvio = await _esta_em_desvio(provider, caso)
    arquivado = caso["status"] == STATUS_ARQUIVADO
    destinos = [] if arquivado else await provider.destinos(caso["tipo_exame"], etapa, "ENCAMINHAMENTO")
    proximas = [] if arquivado or em_desvio else await provider.destinos(caso["tipo_exame"], etapa, "AVANCO")
    return {
        **caso,
        "amostras": amostras,
        "acoes": {
            "pode_concluir": bool(responsavel and proximas),
            "pode_retornar": bool(responsavel and em_desvio),
            "destinos_encaminhamento": destinos if responsavel else [],
        },
    }


# --------------------------------------------------------------------------- #
# UC017 - Concluir etapa com validação                                         #
# --------------------------------------------------------------------------- #
async def concluir_etapa(
    caso_id: int, usuario: Dict[str, Any], ip: Optional[str], provider: CasoPostgresProvider
) -> Dict[str, Any]:
    caso = await _caso_ou_404(provider, caso_id)
    etapa = caso["etapa_atual"]
    if caso["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Caso já arquivado.")
    _exigir_perfil(usuario, PERFIS_POR_ETAPA.get(etapa, set()), f"concluir a etapa {etapa}")
    if await _esta_em_desvio(provider, caso):
        raise HTTPException(status_code=409, detail="Caso em encaminhamento: use 'retornar' para devolvê-lo à etapa de origem.")
    await _exigir_sem_pendencias(provider, caso_id)

    proximas = await provider.destinos(caso["tipo_exame"], etapa, "AVANCO")
    if not proximas:
        raise HTTPException(status_code=409, detail=f"Não há transição configurada a partir de {etapa} para {caso['tipo_exame']}.")
    destino = proximas[0]
    status = _status_derivado(destino)
    agora = _agora()
    try:
        await provider.inserir_movimentacao(
            {
                "caso_id": caso_id, "tipo": "CONCLUSAO", "etapa_origem": etapa,
                "etapa_destino": destino, "motivo": None, "usuario": _login(usuario), "agora": agora,
            }
        )
        await provider.atualizar_etapa(caso_id, destino, status, agora)
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="CONCLUIR_ETAPA", caso_id=caso_id,
            anteriores={"etapa_atual": etapa, "status": caso["status"]},
            novos={"etapa_atual": destino, "status": status},
        )
        await provider.commit()
    except Exception:
        await provider.rollback()
        raise
    return await obter_caso(caso_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC012 - Encaminhar ou retornar caso                                          #
# --------------------------------------------------------------------------- #
async def encaminhar_caso(
    caso_id: int, destino: str, motivo: Optional[str], usuario: Dict[str, Any],
    ip: Optional[str], provider: CasoPostgresProvider,
) -> Dict[str, Any]:
    texto = _motivo_obrigatorio(motivo)
    destino = (destino or "").strip().upper()
    caso = await _caso_ou_404(provider, caso_id)
    etapa = caso["etapa_atual"]
    if caso["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Caso arquivado não pode ser encaminhado.")
    _exigir_perfil(usuario, PERFIS_POR_ETAPA.get(etapa, set()), f"encaminhar a partir de {etapa}")

    permitidos = await provider.destinos(caso["tipo_exame"], etapa, "ENCAMINHAMENTO")
    if destino not in permitidos:
        raise HTTPException(
            status_code=409,
            detail=f"Destino {destino or '(vazio)'} não é permitido a partir de {etapa} para {caso['tipo_exame']}.",
        )
    status = _status_derivado(destino)
    agora = _agora()
    try:
        await provider.inserir_movimentacao(
            {
                "caso_id": caso_id, "tipo": "ENCAMINHAMENTO", "etapa_origem": etapa,
                "etapa_destino": destino, "motivo": texto, "usuario": _login(usuario), "agora": agora,
            }
        )
        await provider.atualizar_etapa(caso_id, destino, status, agora)
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="ENCAMINHAR_CASO", caso_id=caso_id,
            anteriores={"etapa_atual": etapa}, novos={"etapa_atual": destino, "motivo": texto},
        )
        await provider.commit()
    except Exception:
        await provider.rollback()
        raise
    return await obter_caso(caso_id, usuario, provider)


async def retornar_caso(
    caso_id: int, motivo: Optional[str], usuario: Dict[str, Any],
    ip: Optional[str], provider: CasoPostgresProvider,
) -> Dict[str, Any]:
    texto = _motivo_obrigatorio(motivo)
    caso = await _caso_ou_404(provider, caso_id)
    etapa = caso["etapa_atual"]
    if caso["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Caso arquivado não pode ser retornado.")
    _exigir_perfil(usuario, PERFIS_POR_ETAPA.get(etapa, set()), f"retornar o caso a partir de {etapa}")

    desvio = await _esta_em_desvio(provider, caso)
    if not desvio:
        raise HTTPException(status_code=409, detail="O caso não está em encaminhamento; não há etapa de origem para retornar.")
    await _exigir_sem_pendencias(provider, caso_id)

    origem = desvio["etapa_origem"]
    status = _status_derivado(origem)
    agora = _agora()
    try:
        await provider.inserir_movimentacao(
            {
                "caso_id": caso_id, "tipo": "RETORNO", "etapa_origem": etapa,
                "etapa_destino": origem, "motivo": texto, "usuario": _login(usuario), "agora": agora,
            }
        )
        await provider.atualizar_etapa(caso_id, origem, status, agora)
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="RETORNAR_CASO", caso_id=caso_id,
            anteriores={"etapa_atual": etapa}, novos={"etapa_atual": origem, "motivo": texto},
        )
        await provider.commit()
    except Exception:
        await provider.rollback()
        raise
    return await obter_caso(caso_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC018 - Histórico do caso                                                    #
# --------------------------------------------------------------------------- #
async def historico_caso(caso_id: int, provider: CasoPostgresProvider) -> List[Dict[str, Any]]:
    await _caso_ou_404(provider, caso_id)
    return await provider.listar_movimentacoes(caso_id)