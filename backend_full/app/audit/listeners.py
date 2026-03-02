from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models import models as orm
from app.audit.context import get_audit_user_id
import structlog

logger = structlog.get_logger()
_registered = False
_PENDING_INSERT_AUDITS_KEY = "pending_insert_audits"
_SENSITIVE_FIELDS = {
    "password",
    "password_hash",
    "secret",
    "secret_hash",
    "token",
    "access_token",
    "refresh_token",
}


def _json_friendly(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def as_dict(obj: Any) -> Dict[str, Any]:
    state = {}
    for attr in inspect(obj).mapper.column_attrs:
        key = attr.key
        value = _json_friendly(getattr(obj, key))
        if key.lower() in _SENSITIVE_FIELDS:
            state[key] = "***"
        else:
            state[key] = value
    return state


def before_flush(session: Session, flush_context, instances):
    for obj in session.new:
        audit = _create_audit(session, obj, "insert", None, as_dict(obj))
        if audit is not None and getattr(obj, "id", None) is None:
            pending = session.info.setdefault(_PENDING_INSERT_AUDITS_KEY, [])
            pending.append((audit, obj))
    for obj in session.deleted:
        _create_audit(session, obj, "delete", as_dict(obj), None)
    for obj in session.dirty:
        if session.is_modified(obj, include_collections=False):
            _create_audit(session, obj, "update", as_dict(obj), as_dict(obj))


def after_flush_postexec(session: Session, flush_context):
    pending = session.info.pop(_PENDING_INSERT_AUDITS_KEY, [])
    for audit, obj in pending:
        pk_val = getattr(obj, "id", None)
        if pk_val is not None:
            audit.record_id = str(pk_val)


def _create_audit(session: Session, obj: Any, action: str, old: Dict | None, new: Dict | None) -> orm.AuditLog | None:
    if isinstance(obj, orm.AuditLog) or isinstance(obj, orm.RequestLog):
        return None
    model_name = obj.__class__.__name__
    pk_val = getattr(obj, "id", None)
    user_id = get_audit_user_id()
    audit = orm.AuditLog(
        model=model_name,
        record_id=str(pk_val),
        action=action,
        old_data=old,
        new_data=new,
        actor=str(user_id) if user_id is not None else None,
    )
    session.add(audit)
    logger.info("audit_event", model=model_name, action=action, record_id=pk_val, user_id=user_id)
    return audit


def register_listeners():
    global _registered
    if _registered:
        return
    event.listen(Session, "before_flush", before_flush, retval=False)
    event.listen(Session, "after_flush_postexec", after_flush_postexec, retval=False)
    _registered = True
