from __future__ import annotations

from contextvars import ContextVar, Token


_audit_user_id_ctx: ContextVar[int | None] = ContextVar("audit_user_id", default=None)


def set_audit_user_id(user_id: int | None) -> Token:
    return _audit_user_id_ctx.set(user_id)


def get_audit_user_id() -> int | None:
    return _audit_user_id_ctx.get()


def reset_audit_user_id(token: Token) -> None:
    _audit_user_id_ctx.reset(token)

