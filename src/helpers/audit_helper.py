"""
Helper Utilitário de Registro de Auditoria e Trilha de Mudanças
================================================================
Função padronizada para registrar logs de auditoria em rotas e controllers.
"""

import json
import logging
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.audit_log import AuditLog, CATEGORIAS_AUDITORIA

logger = logging.getLogger("audit")


async def registrar_auditoria(
    db: AsyncSession,
    usuario: str,
    categoria: str,
    acao: str,
    recurso: str,
    dados_anteriores: Optional[Any] = None,
    dados_novos: Optional[Any] = None,
    ip_origem: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    """
    Registra um evento de auditoria no banco de dados local da aplicação.

    `categoria` deve ser SEGURANCA, NEGOCIO_CLINICO ou CONFIGURACAO (ValueError caso contrário).

    `commit` (padrão True): grava o log imediatamente, em transação própria.
    Use `commit=False` quando a alteração auditada estiver na MESMA sessão: o log é apenas
    enviado ao banco (flush) e só é gravado no commit do chamador, junto com a alteração.
    Assim, ou os dois são gravados, ou nenhum é (RN-04).

    Exemplos usando os perfis reais do sistema (ADMINISTRADOR, MEDICO, ENFERMAGEM):
        # 1. Categoria SEGURANCA (Ex: ADMINISTRADOR alterando perfil):
        await registrar_auditoria(
            db=session,
            usuario="gestor.admin",
            categoria="SEGURANCA",
            acao="ALTERAR_PERFIL_USUARIO",
            recurso="usuario:joao.silva",
            dados_anteriores={"perfil": "ENFERMAGEM"},
            dados_novos={"perfil": "MEDICO"},
            ip_origem=request.client.host
        )

        # 2. Categoria NEGOCIO_CLINICO (Ex: MEDICO concedendo alta):
        await registrar_auditoria(
            db=session,
            usuario="dr.carlos",
            categoria="NEGOCIO_CLINICO",
            acao="REGISTRAR_ALTA_PACIENTE",
            recurso="paciente:12345",
            dados_anteriores={"status_internacao": "EM_UTI"},
            dados_novos={"status_internacao": "ALTA_MEDICA"},
            ip_origem=request.client.host
        )
    """
    categoria = (categoria or "").upper()
    if categoria not in CATEGORIAS_AUDITORIA:
        raise ValueError(f"Categoria de auditoria inválida: '{categoria}'. Use uma de {CATEGORIAS_AUDITORIA}.")

    try:
        str_anteriores = json.dumps(dados_anteriores, ensure_ascii=False, default=str) if dados_anteriores is not None else None
        str_novos = json.dumps(dados_novos, ensure_ascii=False, default=str) if dados_novos is not None else None

        log_entry = AuditLog(
            usuario=usuario,
            categoria=categoria,
            acao=acao.upper(),
            recurso=recurso,
            dados_anteriores=str_anteriores,
            dados_novos=str_novos,
            ip_origem=ip_origem
        )

        db.add(log_entry)
        if commit:
            await db.commit()
            await db.refresh(log_entry)
        else:
            await db.flush()

        logger.info(f"AuditLog #{log_entry.id} registrado: [{categoria}] {usuario} -> {acao} em {recurso}")
        return log_entry

    except Exception as e:
        # Só o tipo do erro vai para o log: a mensagem pode conter dados do registro (RNF007).
        logger.error(f"Erro ao gravar log de auditoria: {e.__class__.__name__}")
        if commit:
            await db.rollback()
        raise
