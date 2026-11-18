"""Controller do módulo de Solicitações (fluxo principal de negócio do SAP).

Cobre: UC002 (abrir solicitação), UC019 (buscar solicitações), UC012 (encaminhar/retornar)
e UC018 (histórico). Concluir uma etapa (UC017) só acontece pela retirada, na Recepção
(``retirada_controller``), ou pelo "Concluído" do formulário de cada fase (``fase_controller``),
que exige os campos obrigatórios (RN-03).

Regras centrais:
* O fluxo permitido por tipo de exame vem do banco (tabela ``fluxo_transicoes``),
  nunca de código (RF005 / RNF011).
* Toda mutação grava movimentação (append-only) e ``audit_logs`` na MESMA
  transação (RF021 / RNF002 / RNF006).
* Dados do AGHU são somente leitura (RNF005).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from ..helpers.audit_helper import registrar_auditoria
from ..helpers.formularios_fase import FASES_POR_ETAPA
from ..providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface
from ..providers.interfaces.solicitacao_provider_interface import SolicitacaoProviderInterface

logger = logging.getLogger("solicitacoes")

#: Tipos com fluxo no SAP. IHQ e RL (Revisão de Lâmina) entram no MVP com fila própria.
TIPOS_EXAME = {"HP", "CO", "CG", "CCV", "IHQ", "RL"}
#: Tipos sempre urgentes (decisão do setor: Congelação).
TIPOS_SEMPRE_URGENTES = {"CO"}
ETAPA_ARQUIVO = "ARQUIVO"
STATUS_EM_ANDAMENTO = "EM_ANDAMENTO"
STATUS_ARQUIVADO = "ARQUIVADO"

# Perfis (RF002), os mesmos do RBAC local (`authorized_users`).
PERFIL_RECEPCAO = "RECEPCAO"
PERFIL_LABORATORIO = "LABORATORIO"
PERFIL_RESIDENTE = "RESIDENTE"
PERFIL_PRECEPTORIA = "PRECEPTORIA"

# Quem é "responsável" por cada etapa (alçada para encaminhar e retornar; concluir segue a matriz dos formulários).
PERFIS_POR_ETAPA: Dict[str, set] = {
    "RECEPCAO": {PERFIL_RECEPCAO},
    # Matriz de perfis do MVP (ver src/helpers/formularios_fase.py).
    "MACROSCOPIA": {PERFIL_RESIDENTE},
    "CONGELACAO": {PERFIL_RESIDENTE, PERFIL_PRECEPTORIA},
    "PROCESSAMENTO": {PERFIL_LABORATORIO},
    "IHQ": {PERFIL_LABORATORIO},
    "REDE_EXTERNA": {PERFIL_LABORATORIO},
    "MICROSCOPIA": {PERFIL_RESIDENTE, PERFIL_PRECEPTORIA},
    "REVISAO": {PERFIL_RESIDENTE, PERFIL_PRECEPTORIA},
}


# --------------------------------------------------------------------------- #
# Utilitários                                                                  #
# --------------------------------------------------------------------------- #
#: Fuso do hospital: o ano do identificador interno é o ano local da abertura da solicitação.
FUSO_HOSPITAL = ZoneInfo("America/Recife")


def _ano_local() -> int:
    """Ano corrente no fuso do hospital (a numeração recomeça a cada ano)."""
    return datetime.now(FUSO_HOSPITAL).year


def formatar_identificador(sigla: str, numero: int, ano: int) -> str:
    """Identificador interno SIGLA-NNNN/AA (ex.: HP-0001/26), definido com o setor."""
    return f"{sigla}-{numero:04d}/{ano % 100:02d}"


def _agora() -> str:
    """Agora em UTC, texto ISO 8601 (formato das datas das solicitações)."""
    return datetime.now(timezone.utc).isoformat()


def _perfil(usuario: Dict[str, Any]) -> str:
    """Perfil do usuário logado (lido do banco por decode_token)."""
    return str(usuario.get("role") or "").upper()


def _login(usuario: Dict[str, Any]) -> str:
    """Login do usuário logado."""
    return str(usuario["username"])


def _status_derivado(etapa: str) -> str:
    """Status derivado da etapa registrada (RF019): nunca informado pelo cliente."""
    return STATUS_ARQUIVADO if etapa == ETAPA_ARQUIVO else STATUS_EM_ANDAMENTO


def _exigir_perfil(usuario: Dict[str, Any], permitidos: set, acao: str) -> None:
    """403 se o perfil do usuário não está entre os permitidos para a ação."""
    if _perfil(usuario) not in permitidos:
        raise HTTPException(status_code=403, detail=f"Seu perfil não tem permissão para {acao}.")


def _motivo_obrigatorio(motivo: Optional[str]) -> str:
    """Motivo sem espaços nas pontas; 422 se vazio."""
    texto = (motivo or "").strip()
    if not texto:
        raise HTTPException(status_code=422, detail="O motivo é obrigatório.")
    return texto


async def _solicitacao_ou_404(provider: SolicitacaoProviderInterface, solicitacao_id: int) -> Dict[str, Any]:
    """Solicitação ativa pelo id ou 404."""
    solicitacao = await provider.buscar_por_id(solicitacao_id)
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    return solicitacao


async def _exigir_sem_pendencias(provider: SolicitacaoProviderInterface, solicitacao_id: int) -> None:
    """409 se a solicitação tem inconformidade aberta (RF019 / RN-03)."""
    if await provider.contar_pendencias_abertas(solicitacao_id) > 0:
        raise HTTPException(
            status_code=409,
            detail="A solicitação possui inconformidade em aberto. Resolva-a antes de prosseguir.",
        )


async def _esta_em_desvio(provider: SolicitacaoProviderInterface, solicitacao: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retorna a movimentação de encaminhamento se a solicitação está aguardando retorno."""
    ultima = await provider.ultima_movimentacao_desvio(solicitacao["id"])
    if ultima and ultima["tipo"] == "ENCAMINHAMENTO" and ultima["etapa_destino"] == solicitacao["etapa_atual"]:
        return ultima
    return None


async def _gravar(
    provider: SolicitacaoProviderInterface,
    *,
    usuario: Dict[str, Any],
    ip: Optional[str],
    acao: str,
    solicitacao_id: int,
    anteriores: Optional[Dict[str, Any]],
    novos: Dict[str, Any],
) -> None:
    """Registra a auditoria NEGOCIO_CLINICO da solicitação na transação do controller (commit=False)."""
    await registrar_auditoria(
        db=provider.session,
        usuario=_login(usuario),
        categoria="NEGOCIO_CLINICO",
        acao=acao,
        recurso=f"solicitacao:{solicitacao_id}",
        dados_anteriores=anteriores,
        dados_novos=novos,
        ip_origem=ip,
        commit=False,  # grava no commit do controller, junto com a alteração (RN-04)
    )


# --------------------------------------------------------------------------- #
# UC002 - Abrir solicitação a partir do AGHU                                    #
# --------------------------------------------------------------------------- #
def _tipo_aghu(cabecalho: Dict[str, Any]) -> str:
    """Tipo do exame deve vir da origem oficial e estar mapeado para o fluxo SAP."""
    tipo = str(cabecalho.get("tipo_exame") or "").strip().upper()
    if tipo not in TIPOS_EXAME:
        raise HTTPException(
            status_code=409,
            detail="Tipo de exame ausente ou não mapeado no AGHU. Solicite validação do mapeamento à TI.",
        )
    return tipo


def _validar_solicitacao(numero_aghu: str) -> str:
    """Número da solicitação só com dígitos; 422 caso contrário."""
    numero = (numero_aghu or "").strip()
    if not numero.isdigit():
        raise HTTPException(status_code=422, detail="Informe um número de solicitação válido.")
    return numero


async def consultar_solicitacao_aghu(
    numero_aghu: str,
    provider: SolicitacaoProviderInterface,
    aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Pré-visualização para a Recepção confirmar antes de abrir a solicitação no SAP."""
    numero = _validar_solicitacao(numero_aghu)
    try:
        cabecalho = await aghu.buscar_solicitacao(numero)
        amostras = await aghu.listar_amostras(numero) if cabecalho else []
    except Exception as erro:  # não expor detalhes do banco (RNF007)
        logger.error("Falha ao consultar o AGHU: %s", erro.__class__.__name__)
        raise HTTPException(status_code=503, detail="AGHU indisponível no momento. Tente novamente em instantes.")
    if not cabecalho:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada no AGHU.")
    existente = await provider.buscar_por_solicitacao(numero)
    return {**cabecalho, "amostras": amostras, "solicitacao_existente": existente["identificador_interno"] if existente else None}


async def abrir_solicitacao(
    numero_aghu: str,
    usuario: Dict[str, Any],
    ip: Optional[str],
    provider: SolicitacaoProviderInterface,
    aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """UC002: abre no SAP a solicitação recebida no AGHU (uma vez só), com identificador interno, amostras, movimentação e auditoria."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "abrir solicitações")
    numero = _validar_solicitacao(numero_aghu)
    if await provider.buscar_por_solicitacao(numero):
        raise HTTPException(status_code=409, detail="Esta solicitação do AGHU já foi aberta no SAP.")

    try:
        cabecalho = await aghu.buscar_solicitacao(numero)
        amostras = await aghu.listar_amostras(numero) if cabecalho else []
    except Exception as erro:  # não expor detalhes do banco (RNF007)
        logger.error("Falha ao consultar o AGHU: %s", erro.__class__.__name__)
        raise HTTPException(status_code=503, detail="AGHU indisponível no momento. Nenhuma solicitação foi aberta.")
    if not cabecalho:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada no AGHU.")
    if not amostras:
        raise HTTPException(status_code=422, detail="A solicitação não possui amostra vinculada.")

    # Nunca aceitar tipo do cliente. Até a validação do mapeamento SQL pelo DBA,
    # bloquear abertura sem tipo do AGHU (fail closed, RNF005).
    tipo = _tipo_aghu(cabecalho)
    etapa_inicial = await provider.etapa_inicial(tipo)
    if not etapa_inicial:
        raise HTTPException(status_code=409, detail=f"Fluxo do exame {tipo} não está configurado.")

    agora = _agora()
    login = _login(usuario)
    try:
        # Número sequencial por sigla e ano, reservado na mesma transação da solicitação.
        ano = _ano_local()
        identificador = formatar_identificador(tipo, await provider.proximo_numero(tipo, ano), ano)
        solicitacao_id = await provider.inserir_solicitacao(
            {
                "identificador_interno": identificador,
                "solicitacao_aghu": numero,
                "paciente_codigo_aghu": str(cabecalho["paciente_codigo_aghu"]),
                "paciente_nome": cabecalho["paciente_nome"],
                "prontuario_aghu": str(cabecalho.get("prontuario_aghu") or "") or None,
                "tipo_exame": tipo,
                "etapa_atual": etapa_inicial,
                "status": _status_derivado(etapa_inicial),
                "urgente": tipo in TIPOS_SEMPRE_URGENTES or bool(cabecalho.get("urgente")),
                "usuario": login,
                "agora": agora,
            }
        )
        for amostra in amostras:
            await provider.inserir_amostra(solicitacao_id, str(amostra["amostra_aghu"]), amostra.get("descricao"))
        await provider.inserir_movimentacao(
            {
                "solicitacao_id": solicitacao_id, "tipo": "ABERTURA", "etapa_origem": None,
                "etapa_destino": etapa_inicial, "motivo": None, "usuario": login, "agora": agora,
            }
        )
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="ABRIR_SOLICITACAO", solicitacao_id=solicitacao_id, anteriores=None,
            novos={
                "identificador_interno": identificador, "solicitacao_aghu": numero,
                "tipo_exame": tipo, "etapa_atual": etapa_inicial, "amostras": len(amostras),
            },
        )
        await provider.commit()
    except IntegrityError:
        await provider.rollback()
        raise HTTPException(status_code=409, detail="Esta solicitação do AGHU já foi aberta no SAP.")
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados da solicitação (RNF007).
        logger.error("Falha em %s: %s", "ABRIR_SOLICITACAO", erro.__class__.__name__)
        raise
    return await obter_solicitacao(solicitacao_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC019 - Buscar solicitações                                                         #
# --------------------------------------------------------------------------- #
async def buscar_solicitacoes(
    filtros: Dict[str, Any], pagina: int, limite: int, provider: SolicitacaoProviderInterface
) -> Dict[str, Any]:
    """UC019: busca paginada de solicitações ativas com os filtros informados."""
    pagina = max(pagina, 1)
    limite = min(max(limite, 1), 100)
    limpos = {k: (v.strip() if isinstance(v, str) else v) or None for k, v in filtros.items()}
    for chave in ("tipo_exame", "etapa", "status"):
        if limpos.get(chave):
            limpos[chave] = limpos[chave].upper()
    itens = await provider.buscar_solicitacoes(limpos, limite, (pagina - 1) * limite)
    total = await provider.contar_busca_solicitacoes(limpos)
    return {"items": itens, "total": total, "pagina": pagina, "limite": limite}


async def obter_solicitacao(solicitacao_id: int, usuario: Dict[str, Any], provider: SolicitacaoProviderInterface) -> Dict[str, Any]:
    """Detalhe da solicitação com amostras e as ações que o perfil pode executar na etapa atual."""
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    amostras = await provider.listar_amostras(solicitacao_id)
    etapa = solicitacao["etapa_atual"]
    perfil = _perfil(usuario)
    responsavel = perfil in PERFIS_POR_ETAPA.get(etapa, set())
    em_desvio = await _esta_em_desvio(provider, solicitacao)
    arquivado = solicitacao["status"] == STATUS_ARQUIVADO
    destinos = [] if arquivado else await provider.destinos(solicitacao["tipo_exame"], etapa, "ENCAMINHAMENTO")
    # Concluir a etapa atual: na Recepção é marcar retirado; nas fases, o "Concluído" do formulário
    # (/api/fases). Não há outro caminho para avançar (RN-03, T4.2).
    if etapa == "RECEPCAO":
        pode_concluir = perfil == PERFIL_RECEPCAO and not arquivado and not em_desvio and not solicitacao.get("retirado_em")
    else:
        fase = FASES_POR_ETAPA.get(etapa)
        tem_saida = em_desvio or bool(await provider.destinos(solicitacao["tipo_exame"], etapa, "AVANCO"))
        pode_concluir = bool(fase and perfil in fase["concluir"] and not arquivado and tem_saida)
    return {
        **solicitacao,
        "amostras": amostras,
        "acoes": {
            "pode_concluir": pode_concluir,
            "pode_retornar": bool(responsavel and em_desvio),
            "destinos_encaminhamento": destinos if responsavel else [],
        },
    }


# --------------------------------------------------------------------------- #
# UC012 - Encaminhar ou retornar solicitação                                          #
# --------------------------------------------------------------------------- #
async def encaminhar_solicitacao(
    solicitacao_id: int, destino: str, motivo: Optional[str], usuario: Dict[str, Any],
    ip: Optional[str], provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """UC012: encaminha a solicitação a um destino permitido pelo fluxo, com motivo obrigatório."""
    texto = _motivo_obrigatorio(motivo)
    destino = (destino or "").strip().upper()
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    etapa = solicitacao["etapa_atual"]
    if solicitacao["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Solicitação arquivada não pode ser encaminhada.")
    _exigir_perfil(usuario, PERFIS_POR_ETAPA.get(etapa, set()), f"encaminhar a partir de {etapa}")

    permitidos = await provider.destinos(solicitacao["tipo_exame"], etapa, "ENCAMINHAMENTO")
    if destino not in permitidos:
        raise HTTPException(
            status_code=409,
            detail=f"Destino {destino or '(vazio)'} não é permitido a partir de {etapa} para {solicitacao['tipo_exame']}.",
        )
    status = _status_derivado(destino)
    agora = _agora()
    try:
        await provider.inserir_movimentacao(
            {
                "solicitacao_id": solicitacao_id, "tipo": "ENCAMINHAMENTO", "etapa_origem": etapa,
                "etapa_destino": destino, "motivo": texto, "usuario": _login(usuario), "agora": agora,
            }
        )
        await provider.atualizar_etapa(solicitacao_id, destino, status, agora)
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="ENCAMINHAR_SOLICITACAO", solicitacao_id=solicitacao_id,
            anteriores={"etapa_atual": etapa}, novos={"etapa_atual": destino, "motivo": texto},
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados da solicitação (RNF007).
        logger.error("Falha em %s: %s", "ENCAMINHAR_SOLICITACAO", erro.__class__.__name__)
        raise
    return await obter_solicitacao(solicitacao_id, usuario, provider)


async def retornar_solicitacao(
    solicitacao_id: int, motivo: Optional[str], usuario: Dict[str, Any],
    ip: Optional[str], provider: SolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """UC012: devolve a solicitação encaminhada à etapa de origem, com motivo obrigatório."""
    texto = _motivo_obrigatorio(motivo)
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    etapa = solicitacao["etapa_atual"]
    if solicitacao["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Solicitação arquivada não pode ser retornada.")
    _exigir_perfil(usuario, PERFIS_POR_ETAPA.get(etapa, set()), f"retornar a solicitação a partir de {etapa}")

    desvio = await _esta_em_desvio(provider, solicitacao)
    if not desvio:
        raise HTTPException(status_code=409, detail="A solicitação não está em encaminhamento; não há etapa de origem para retornar.")
    await _exigir_sem_pendencias(provider, solicitacao_id)

    origem = desvio["etapa_origem"]
    status = _status_derivado(origem)
    agora = _agora()
    try:
        await provider.inserir_movimentacao(
            {
                "solicitacao_id": solicitacao_id, "tipo": "RETORNO", "etapa_origem": etapa,
                "etapa_destino": origem, "motivo": texto, "usuario": _login(usuario), "agora": agora,
            }
        )
        await provider.atualizar_etapa(solicitacao_id, origem, status, agora)
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="RETORNAR_SOLICITACAO", solicitacao_id=solicitacao_id,
            anteriores={"etapa_atual": etapa}, novos={"etapa_atual": origem, "motivo": texto},
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados da solicitação (RNF007).
        logger.error("Falha em %s: %s", "RETORNAR_SOLICITACAO", erro.__class__.__name__)
        raise
    return await obter_solicitacao(solicitacao_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC018 - Histórico da solicitação                                                    #
# --------------------------------------------------------------------------- #
async def historico_solicitacao(solicitacao_id: int, provider: SolicitacaoProviderInterface) -> List[Dict[str, Any]]:
    """UC018: movimentações da solicitação em ordem cronológica."""
    await _solicitacao_ou_404(provider, solicitacao_id)
    return await provider.listar_movimentacoes(solicitacao_id)

# --------------------------------------------------------------------------- #
# Conciliação cadastral do AGHU (consulta + sincronização explícita)           #
# --------------------------------------------------------------------------- #
async def _comparar_com_aghu(
    solicitacao: Dict[str, Any], aghu: AghuSolicitacaoProviderInterface
) -> Dict[str, Any]:
    """Consulta a origem; mudanças de vínculo ou tipo exigem análise humana, não merge."""
    try:
        origem = await aghu.buscar_solicitacao(str(solicitacao["solicitacao_aghu"]))
    except Exception as erro:
        logger.error("Falha ao conferir cadastro no AGHU: %s", erro.__class__.__name__)
        raise HTTPException(status_code=503, detail="AGHU indisponível. O cadastro local foi preservado.")
    if not origem:
        raise HTTPException(status_code=409, detail="Solicitação não localizada no AGHU; acione a TI.")
    if str(origem.get("paciente_codigo_aghu")) != str(solicitacao["paciente_codigo_aghu"]):
        raise HTTPException(status_code=409, detail="Vínculo de paciente divergente no AGHU. Não é possível sincronizar automaticamente.")
    if _tipo_aghu(origem) != solicitacao["tipo_exame"]:
        raise HTTPException(status_code=409, detail="Tipo de exame divergente no AGHU. Encaminhe para revisão da gestão.")

    atual = {
        "paciente_nome": str(origem.get("paciente_nome") or "").strip(),
        "prontuario_aghu": str(origem.get("prontuario_aghu") or "").strip() or None,
    }
    if not atual["paciente_nome"]:
        raise HTTPException(status_code=409, detail="Cadastro incompleto no AGHU: nome não informado.")

    anterior = {
        "paciente_nome": str(solicitacao["paciente_nome"]).strip(),
        "prontuario_aghu": str(solicitacao.get("prontuario_aghu") or "").strip() or None,
    }
    divergencias = {
        chave: {"anterior": anterior[chave], "atual_aghu": valor}
        for chave, valor in atual.items() if anterior[chave] != valor
    }
    return {"divergencias": divergencias, "dados_aghu": atual}


async def conferir_dados_aghu(
    solicitacao_id: int, usuario: Dict[str, Any], provider: SolicitacaoProviderInterface,
    aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Compara o snapshot cifrado da solicitação com a fonte; não altera registros."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "conferir dados cadastrais")
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    resultado = await _comparar_com_aghu(solicitacao, aghu)
    return {
        "solicitacao_id": solicitacao_id, "atualizacao_pendente": bool(resultado["divergencias"]),
        "divergencias": resultado["divergencias"],
        "ultima_sincronizacao_aghu": solicitacao.get("ultima_sincronizacao_aghu"),
        "pode_sincronizar": _perfil(usuario) == PERFIL_RECEPCAO and solicitacao["status"] != STATUS_ARQUIVADO,
    }


async def sincronizar_dados_aghu(
    solicitacao_id: int, usuario: Dict[str, Any], ip: Optional[str],
    provider: SolicitacaoProviderInterface, aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Refaz comparação no POST (evita confiar no preview), atualiza snapshot e audita."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "sincronizar dados cadastrais")
    solicitacao = await _solicitacao_ou_404(provider, solicitacao_id)
    if solicitacao["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Solicitação arquivada: preserve o snapshot e encaminhe a correção à gestão.")
    resultado = await _comparar_com_aghu(solicitacao, aghu)
    if not resultado["divergencias"]:
        return await obter_solicitacao(solicitacao_id, usuario, provider)
    agora = _agora()
    novos = resultado["dados_aghu"]
    anteriores = {chave: solicitacao.get(chave) for chave in novos}
    try:
        await provider.atualizar_dados_aghu(
            solicitacao_id, novos["paciente_nome"], novos["prontuario_aghu"], agora,
        )
        await provider.inserir_movimentacao({
            "solicitacao_id": solicitacao_id, "tipo": "SINCRONIZACAO_AGHU",
            "etapa_origem": solicitacao["etapa_atual"], "etapa_destino": solicitacao["etapa_atual"],
            "motivo": "Atualização cadastral validada no AGHU (snapshot local)",
            "usuario": _login(usuario), "agora": agora,
        })
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="SINCRONIZAR_CADASTRO_AGHU",
            solicitacao_id=solicitacao_id, anteriores=anteriores, novos=novos,
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        logger.error("Falha em SINCRONIZAR_CADASTRO_AGHU: %s", erro.__class__.__name__)
        raise
    return await obter_solicitacao(solicitacao_id, usuario, provider)
