"""Provisionamento local controlado por operador do servidor, SEM endpoint público.

Uso: python -m scripts.provision_sap_user --username ... --role RECEPCAO \
      --actor login.operador --confirm
"""
import argparse
import asyncio
import json
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.auth.auth import ROLES, auth_handler, normalize_username, _role_group_policy
from src.models.audit_log import AuditLog
from src.models.authorized_user import AuthorizedUser


def arguments():
    parser = argparse.ArgumentParser(description="Provisiona usuário autorizado do SAP")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", required=True, choices=sorted(ROLES))
    parser.add_argument("--actor", required=True, help="Login do operador autorizado")
    parser.add_argument("--deactivate", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Confirma alteração em DB local")
    return parser.parse_args()


async def main():
    args = arguments()
    if not args.confirm:
        raise SystemExit("Alteração não executada. Informe --confirm após validação pela gestão.")
    username = normalize_username(args.username)
    actor = normalize_username(args.actor)
    info = await asyncio.to_thread(auth_handler.search_ad_user, username)
    if not info.get("exists") or not info.get("enabled"):
        raise SystemExit("Usuário não existe ou está desativado no AD/Mock")
    expected = _role_group_policy().get(args.role)
    if expected and not expected.intersection(g.casefold() for g in info.get("groups", [])):
        raise SystemExit("Usuário não pertence aos grupos AD exigidos para o perfil")

    dsn = os.getenv("SQLITE_DSN") or os.getenv("APP_DB_URL")
    if not dsn:
        raise SystemExit("APP_DB_URL ou SQLITE_DSN deve estar explicitamente configurado")
    engine = create_async_engine(dsn)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            result = await db.execute(select(AuthorizedUser).where(AuthorizedUser.username == username))
            obj = result.scalar_one_or_none()
            previous = {"role": obj.role, "active": bool(obj.active)} if obj else None
            if obj:
                obj.role = args.role
                obj.active = not args.deactivate
                obj.updated_at = datetime.now(timezone.utc)
            else:
                obj = AuthorizedUser(username=username, role=args.role, active=not args.deactivate)
                db.add(obj)
            new = {"role": args.role, "active": not args.deactivate}
            db.add(AuditLog(usuario=actor, categoria="SEGURANCA", acao="ALTERAR_ACESSO_SAP",
                            recurso=f"usuario:{username}",
                            dados_anteriores=json.dumps(previous), dados_novos=json.dumps(new)))
            await db.commit()
            print(f"Autorização atualizada: {username} / {args.role} / ativo={not args.deactivate}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
