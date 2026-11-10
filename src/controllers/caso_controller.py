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
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from ..helpers.audit_helper import registrar_auditoria
from ..providers.interfaces.aghu_solicitacao_provider_interface import AghuSolicitacaoProviderInterface
from ..providers.interfaces.caso_provider_interface import CasoProviderInterface

logger = logging.getLogger("casos")

TIPOS_EXAME = {"HP", "CO", "CG", "CCV"}
ETAPA_ARQUIVO = "ARQUIVO"
STATUS_EM_ANDAMENTO = "EM_ANDAMENTO"
STATUS_ARQUIVADO = "ARQUIVADO"

# Perfis (RF002), os mesmos do RBAC local (`authorized_users`).
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
#: Fuso do hospital: o ano do identificador interno é o ano local da abertura do caso.
FUSO_HOSPITAL = ZoneInfo("America/Recife")


def _ano_local() -> int:
    """Ano corrente no fuso do hospital (a numeração recomeça a cada ano)."""
    return datetime.now(FUSO_HOSPITAL).year


def formatar_identificador(sigla: str, numero: int, ano: int) -> str:
    """Identificador interno SIGLA-NNNN/AA (ex.: HP-0001/26), definido com o setor."""
    return f"{sigla}-{numero:04d}/{ano % 100:02d}"


def _agora() -> str:
    """Agora em UTC, texto ISO 8601 (formato das datas dos casos)."""
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


async def _caso_ou_404(provider: CasoProviderInterface, caso_id: int) -> Dict[str, Any]:
    """Caso ativo pelo id ou 404."""
    caso = await provider.buscar_por_id(caso_id)
    if not caso:
        raise HTTPException(status_code=404, detail="Caso não encontrado.")
    return caso


async def _exigir_sem_pendencias(provider: CasoProviderInterface, caso_id: int) -> None:
    """409 se o caso tem inconformidade aberta (RF019 / RN-03)."""
    if await provider.contar_pendencias_abertas(caso_id) > 0:
        raise HTTPException(
            status_code=409,
            detail="O caso possui inconformidade em aberto. Resolva-a antes de prosseguir.",
        )


async def _esta_em_desvio(provider: CasoProviderInterface, caso: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retorna a movimentação de encaminhamento se o caso está aguardando retorno."""
    ultima = await provider.ultima_movimentacao_desvio(caso["id"])
    if ultima and ultima["tipo"] == "ENCAMINHAMENTO" and ultima["etapa_destino"] == caso["etapa_atual"]:
        return ultima
    return None


async def _gravar(
    provider: CasoProviderInterface,
    *,
    usuario: Dict[str, Any],
    ip: Optional[str],
    acao: str,
    caso_id: int,
    anteriores: Optional[Dict[str, Any]],
    novos: Dict[str, Any],
) -> None:
    """Registra a auditoria NEGOCIO_CLINICO do caso na transação do controller (commit=False)."""
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
def _tipo_aghu(cabecalho: Dict[str, Any]) -> str:
    """Tipo do exame deve vir da origem oficial e estar mapeado para o fluxo SAP."""
    tipo = str(cabecalho.get("tipo_exame") or "").strip().upper()
    if tipo not in TIPOS_EXAME:
        raise HTTPException(
            status_code=409,
            detail="Tipo de exame ausente ou não mapeado no AGHU. Solicite validação do mapeamento à TI.",
        )
    return tipo


def _validar_solicitacao(solicitacao: str) -> str:
    """Número da solicitação só com dígitos; 422 caso contrário."""
    numero = (solicitacao or "").strip()
    if not numero.isdigit():
        raise HTTPException(status_code=422, detail="Informe um número de solicitação válido.")
    return numero


async def consultar_solicitacao_aghu(
    solicitacao: str,
    provider: CasoProviderInterface,
    aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Pré-visualização para a Recepção confirmar antes de criar o caso."""
    numero = _validar_solicitacao(solicitacao)
    try:
        cabecalho = await aghu.buscar_solicitacao(numero)
        amostras = await aghu.listar_amostras(numero) if cabecalho else []
    except Exception as erro:  # não expor detalhes do banco (RNF007)
        logger.error("Falha ao consultar o AGHU: %s", erro.__class__.__name__)
        raise HTTPException(status_code=503, detail="AGHU indisponível no momento. Tente novamente em instantes.")
    if not cabecalho:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada no AGHU.")
    existente = await provider.buscar_por_solicitacao(numero)
    return {**cabecalho, "amostras": amostras, "caso_existente": existente["identificador_interno"] if existente else None}


async def abrir_caso(
    solicitacao: str,
    usuario: Dict[str, Any],
    ip: Optional[str],
    provider: CasoProviderInterface,
    aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """UC002: cria o caso (um por solicitação) com identificador interno, amostras, movimentação e auditoria."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "abrir casos")
    numero = _validar_solicitacao(solicitacao)
    if await provider.buscar_por_solicitacao(numero):
        raise HTTPException(status_code=409, detail="Já existe um caso aberto para esta solicitação.")

    try:
        cabecalho = await aghu.buscar_solicitacao(numero)
        amostras = await aghu.listar_amostras(numero) if cabecalho else []
    except Exception as erro:  # não expor detalhes do banco (RNF007)
        logger.error("Falha ao consultar o AGHU: %s", erro.__class__.__name__)
        raise HTTPException(status_code=503, detail="AGHU indisponível no momento. Nenhum caso foi criado.")
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
        # Número sequencial por sigla e ano, reservado na mesma transação do caso.
        ano = _ano_local()
        identificador = formatar_identificador(tipo, await provider.proximo_numero(tipo, ano), ano)
        caso_id = await provider.inserir_caso(
            {
                "identificador_interno": identificador,
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
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados do caso (RNF007).
        logger.error("Falha em %s: %s", "ABRIR_CASO", erro.__class__.__name__)
        raise
    return await obter_caso(caso_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC019 - Buscar casos                                                         #
# --------------------------------------------------------------------------- #
async def listar_casos(
    filtros: Dict[str, Any], pagina: int, limite: int, provider: CasoProviderInterface
) -> Dict[str, Any]:
    """UC019: busca paginada de casos ativos com os filtros informados."""
    pagina = max(pagina, 1)
    limite = min(max(limite, 1), 100)
    limpos = {k: (v.strip() if isinstance(v, str) else v) or None for k, v in filtros.items()}
    for chave in ("tipo_exame", "etapa", "status"):
        if limpos.get(chave):
            limpos[chave] = limpos[chave].upper()
    itens = await provider.listar_casos(limpos, limite, (pagina - 1) * limite)
    total = await provider.contar_casos(limpos)
    return {"items": itens, "total": total, "pagina": pagina, "limite": limite}


async def obter_caso(caso_id: int, usuario: Dict[str, Any], provider: CasoProviderInterface) -> Dict[str, Any]:
    """Detalhe do caso com amostras e as ações que o perfil pode executar na etapa atual."""
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
    caso_id: int, usuario: Dict[str, Any], ip: Optional[str], provider: CasoProviderInterface
) -> Dict[str, Any]:
    """UC017: avança o caso para a próxima etapa do fluxo, se não houver pendências."""
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
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados do caso (RNF007).
        logger.error("Falha em %s: %s", "CONCLUIR_ETAPA", erro.__class__.__name__)
        raise
    return await obter_caso(caso_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC012 - Encaminhar ou retornar caso                                          #
# --------------------------------------------------------------------------- #
async def encaminhar_caso(
    caso_id: int, destino: str, motivo: Optional[str], usuario: Dict[str, Any],
    ip: Optional[str], provider: CasoProviderInterface,
) -> Dict[str, Any]:
    """UC012: encaminha o caso a um destino permitido pelo fluxo, com motivo obrigatório."""
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
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados do caso (RNF007).
        logger.error("Falha em %s: %s", "ENCAMINHAR_CASO", erro.__class__.__name__)
        raise
    return await obter_caso(caso_id, usuario, provider)


async def retornar_caso(
    caso_id: int, motivo: Optional[str], usuario: Dict[str, Any],
    ip: Optional[str], provider: CasoProviderInterface,
) -> Dict[str, Any]:
    """UC012: devolve o caso encaminhado à etapa de origem, com motivo obrigatório."""
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
    except Exception as erro:
        await provider.rollback()
        # Padrão de log de erro: ação + tipo da exceção, sem dados do caso (RNF007).
        logger.error("Falha em %s: %s", "RETORNAR_CASO", erro.__class__.__name__)
        raise
    return await obter_caso(caso_id, usuario, provider)


# --------------------------------------------------------------------------- #
# UC018 - Histórico do caso                                                    #
# --------------------------------------------------------------------------- #
async def historico_caso(caso_id: int, provider: CasoProviderInterface) -> List[Dict[str, Any]]:
    """UC018: movimentações do caso em ordem cronológica."""
    await _caso_ou_404(provider, caso_id)
    return await provider.listar_movimentacoes(caso_id)

# --------------------------------------------------------------------------- #
# Conciliação cadastral do AGHU (consulta + sincronização explícita)           #
# --------------------------------------------------------------------------- #
async def _comparar_com_aghu(
    caso: Dict[str, Any], aghu: AghuSolicitacaoProviderInterface
) -> Dict[str, Any]:
    """Consulta a origem; mudanças de vínculo ou tipo exigem análise humana, não merge."""
    try:
        origem = await aghu.buscar_solicitacao(str(caso["solicitacao_aghu"]))
    except Exception as erro:
        logger.error("Falha ao conferir cadastro no AGHU: %s", erro.__class__.__name__)
        raise HTTPException(status_code=503, detail="AGHU indisponível. O cadastro local foi preservado.")
    if not origem:
        raise HTTPException(status_code=409, detail="Solicitação não localizada no AGHU; acione a TI.")
    if str(origem.get("paciente_codigo_aghu")) != str(caso["paciente_codigo_aghu"]):
        raise HTTPException(status_code=409, detail="Vínculo de paciente divergente no AGHU. Não é possível sincronizar automaticamente.")
    if _tipo_aghu(origem) != caso["tipo_exame"]:
        raise HTTPException(status_code=409, detail="Tipo de exame divergente no AGHU. Encaminhe para revisão da gestão.")

    atual = {
        "paciente_nome": str(origem.get("paciente_nome") or "").strip(),
        "prontuario_aghu": str(origem.get("prontuario_aghu") or "").strip() or None,
    }
    if not atual["paciente_nome"]:
        raise HTTPException(status_code=409, detail="Cadastro incompleto no AGHU: nome não informado.")

    anterior = {
        "paciente_nome": str(caso["paciente_nome"]).strip(),
        "prontuario_aghu": str(caso.get("prontuario_aghu") or "").strip() or None,
    }
    divergencias = {
        chave: {"anterior": anterior[chave], "atual_aghu": valor}
        for chave, valor in atual.items() if anterior[chave] != valor
    }
    return {"divergencias": divergencias, "dados_aghu": atual}


async def conferir_dados_aghu(
    caso_id: int, usuario: Dict[str, Any], provider: CasoProviderInterface,
    aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Compara o snapshot cifrado do caso com a fonte; não altera registros."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "conferir dados cadastrais")
    caso = await _caso_ou_404(provider, caso_id)
    resultado = await _comparar_com_aghu(caso, aghu)
    return {
        "caso_id": caso_id, "atualizacao_pendente": bool(resultado["divergencias"]),
        "divergencias": resultado["divergencias"],
        "ultima_sincronizacao_aghu": caso.get("ultima_sincronizacao_aghu"),
        "pode_sincronizar": _perfil(usuario) == PERFIL_RECEPCAO and caso["status"] != STATUS_ARQUIVADO,
    }


async def sincronizar_dados_aghu(
    caso_id: int, usuario: Dict[str, Any], ip: Optional[str],
    provider: CasoProviderInterface, aghu: AghuSolicitacaoProviderInterface,
) -> Dict[str, Any]:
    """Refaz comparação no POST (evita confiar no preview), atualiza snapshot e audita."""
    _exigir_perfil(usuario, {PERFIL_RECEPCAO}, "sincronizar dados cadastrais")
    caso = await _caso_ou_404(provider, caso_id)
    if caso["status"] == STATUS_ARQUIVADO:
        raise HTTPException(status_code=409, detail="Caso arquivado: preserve o snapshot e encaminhe a correção à gestão.")
    resultado = await _comparar_com_aghu(caso, aghu)
    if not resultado["divergencias"]:
        return await obter_caso(caso_id, usuario, provider)
    agora = _agora()
    novos = resultado["dados_aghu"]
    anteriores = {chave: caso.get(chave) for chave in novos}
    try:
        await provider.atualizar_dados_aghu(
            caso_id, novos["paciente_nome"], novos["prontuario_aghu"], agora,
        )
        await provider.inserir_movimentacao({
            "caso_id": caso_id, "tipo": "SINCRONIZACAO_AGHU",
            "etapa_origem": caso["etapa_atual"], "etapa_destino": caso["etapa_atual"],
            "motivo": "Atualização cadastral validada no AGHU (snapshot local)",
            "usuario": _login(usuario), "agora": agora,
        })
        await _gravar(
            provider, usuario=usuario, ip=ip, acao="SINCRONIZAR_CADASTRO_AGHU",
            caso_id=caso_id, anteriores=anteriores, novos=novos,
        )
        await provider.commit()
    except Exception as erro:
        await provider.rollback()
        logger.error("Falha em SINCRONIZAR_CADASTRO_AGHU: %s", erro.__class__.__name__)
        raise
    return await obter_caso(caso_id, usuario, provider)
