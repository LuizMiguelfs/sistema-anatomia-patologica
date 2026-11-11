"""
Controller de Pacientes
=======================
Regras de negócio do cadastro de pacientes: validação de CPF/CNS e datas, duplicidade,
permissões de escrita da fonte de dados e trilha de auditoria (NEGOCIO_CLINICO).
O controller não sabe qual fonte está em uso (CSV ou AGHU): usa apenas a interface do provedor.
"""

import re
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..helpers.audit_helper import registrar_auditoria
from ..helpers.string_helper import (
    formatar_cpf,
    normalizar_nome,
    somente_digitos,
    validar_cns,
    validar_cpf,
)
from ..providers.interfaces.paciente_provider_interface import PacienteProviderInterface

CATEGORIA_AUDITORIA = "NEGOCIO_CLINICO"
DATA_NASCIMENTO_MINIMA = date(1900, 1, 1)
MIN_CARACTERES_BUSCA_NOME = 3
TERMO_NUMERICO = re.compile(r"\d[\d.\-\s]*")


def obter_capacidades(provider: PacienteProviderInterface) -> Dict[str, Any]:
    """Retorna a fonte de dados ativa e o que ela permite (usado pelo frontend para exibir ações)."""
    # Pacientes são de responsabilidade do AGHU. O CSV é um catálogo offline de
    # testes, nunca uma fonte autorizada para cadastro via API do SAP.
    return {"fonte": provider.fonte, "escrita": False, "exclusao": False}


async def listar_pacientes(
    provider: PacienteProviderInterface,
    termo: Optional[str] = None,
    limite: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Lista/busca pacientes. Buscas por nome exigem ao menos 3 caracteres para evitar
    varreduras pesadas no AGHU; termos numéricos (código, CPF, CNS) não têm mínimo.
    """
    termo = (termo or "").strip() or None
    if termo and TERMO_NUMERICO.fullmatch(termo):
        termo = somente_digitos(termo)
    elif termo and len(termo) < MIN_CARACTERES_BUSCA_NOME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Informe ao menos {MIN_CARACTERES_BUSCA_NOME} caracteres para buscar por nome.",
        )
    return await provider.listar_pacientes(termo=termo, limite=limite, offset=offset)


async def obter_paciente_por_codigo(codigo: int, provider: PacienteProviderInterface) -> Dict[str, Any]:
    """Retorna o paciente ou 404."""
    paciente = await provider.obter_paciente_por_codigo(codigo)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado.")
    return paciente


def _exigir_capacidade(provider: PacienteProviderInterface, capacidade: str, mensagem: str) -> None:
    """Bloqueia a operação (403) se a fonte de dados não permitir a capacidade pedida."""
    if not provider.capacidades().get(capacidade, False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mensagem)


def _preparar_dados(dados: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza e valida os campos de entrada; lança 400 com mensagem clara em caso de erro."""
    preparado = dict(dados)

    preparado["nome"] = normalizar_nome(dados.get("nome"))
    if not preparado["nome"] or len(preparado["nome"]) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O nome deve ter ao menos 3 caracteres.")
    preparado["nome_mae"] = normalizar_nome(dados.get("nome_mae"))
    preparado["nome_pai"] = normalizar_nome(dados.get("nome_pai"))

    dt_nascimento: date = dados["dt_nascimento"]
    if dt_nascimento > date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A data de nascimento não pode estar no futuro.")
    if dt_nascimento < DATA_NASCIMENTO_MINIMA:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data de nascimento inválida (anterior a 1900).")

    cpf = somente_digitos(dados.get("cpf"))
    if cpf:
        if not validar_cpf(cpf):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CPF inválido.")
        preparado["cpf"] = formatar_cpf(cpf)
    else:
        preparado["cpf"] = None

    cns = somente_digitos(dados.get("cns"))
    if cns:
        if not validar_cns(cns):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CNS (Cartão Nacional de Saúde) inválido.")
        preparado["cns"] = cns
    else:
        preparado["cns"] = None

    return preparado


async def _garantir_cpf_unico(
    provider: PacienteProviderInterface, cpf: Optional[str], ignorar_codigo: Optional[int] = None
) -> None:
    """Impede dois pacientes ativos com o mesmo CPF (409)."""
    if cpf and await provider.existe_cpf(somente_digitos(cpf), ignorar_codigo=ignorar_codigo):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um paciente ativo com este CPF.")


async def criar_paciente(
    dados: Dict[str, Any],
    provider: PacienteProviderInterface,
    db: AsyncSession,
    usuario: str,
    ip_origem: Optional[str] = None,
) -> Dict[str, Any]:
    """Cadastra um paciente e registra auditoria (CRIAR_PACIENTE)."""
    _exigir_capacidade(provider, "escrita", "A fonte de dados atual (AGHU) é somente leitura.")
    preparado = _preparar_dados(dados)
    await _garantir_cpf_unico(provider, preparado["cpf"])

    try:
        criado = await provider.criar_paciente(preparado)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A fonte de dados atual (AGHU) é somente leitura.")

    await registrar_auditoria(
        db=db,
        usuario=usuario,
        categoria=CATEGORIA_AUDITORIA,
        acao="CRIAR_PACIENTE",
        recurso=f"paciente:{criado['codigo']}",
        dados_anteriores=None,
        dados_novos=criado,
        ip_origem=ip_origem,
    )
    return criado


async def atualizar_paciente(
    codigo: int,
    dados: Dict[str, Any],
    provider: PacienteProviderInterface,
    db: AsyncSession,
    usuario: str,
    ip_origem: Optional[str] = None,
) -> Dict[str, Any]:
    """Altera um paciente e registra auditoria com o estado anterior e o novo (ALTERAR_PACIENTE)."""
    _exigir_capacidade(provider, "escrita", "A fonte de dados atual (AGHU) é somente leitura.")
    anterior = await obter_paciente_por_codigo(codigo, provider)
    preparado = _preparar_dados(dados)
    await _garantir_cpf_unico(provider, preparado["cpf"], ignorar_codigo=codigo)

    try:
        atualizado = await provider.atualizar_paciente(codigo, preparado)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A fonte de dados atual (AGHU) é somente leitura.")
    if atualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado.")

    await registrar_auditoria(
        db=db,
        usuario=usuario,
        categoria=CATEGORIA_AUDITORIA,
        acao="ALTERAR_PACIENTE",
        recurso=f"paciente:{codigo}",
        dados_anteriores=anterior,
        dados_novos=atualizado,
        ip_origem=ip_origem,
    )
    return atualizado


async def excluir_paciente(
    codigo: int,
    provider: PacienteProviderInterface,
    db: AsyncSession,
    usuario: str,
    ip_origem: Optional[str] = None,
) -> None:
    """Exclusão LÓGICA do paciente (o registro é preservado) com auditoria (EXCLUIR_PACIENTE)."""
    _exigir_capacidade(provider, "exclusao", "A fonte de dados atual não permite excluir pacientes.")
    try:
        excluido = await provider.excluir_paciente(codigo)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A fonte de dados atual não permite excluir pacientes.")
    if excluido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado.")

    await registrar_auditoria(
        db=db,
        usuario=usuario,
        categoria=CATEGORIA_AUDITORIA,
        acao="EXCLUIR_PACIENTE",
        recurso=f"paciente:{codigo}",
        dados_anteriores=excluido,
        dados_novos={"excluido": True, "tipo_exclusao": "LOGICA"},
        ip_origem=ip_origem,
    )
