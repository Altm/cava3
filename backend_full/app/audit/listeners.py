from typing import Any, Dict
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.models import models as orm
import structlog

logger = structlog.get_logger()


def as_dict(obj: Any) -> Dict[str, Any]:
    state = {}
    for attr in inspect(obj).mapper.column_attrs:
        key = attr.key
        state[key] = getattr(obj, key)
    return state


def before_flush(session: Session, flush_context, instances):
    for obj in session.new:
        _create_audit(session, obj, "insert", None, as_dict(obj))
    for obj in session.deleted:
        _create_audit(session, obj, "delete", as_dict(obj), None)
    for obj in session.dirty:
        if session.is_modified(obj, include_collections=False):
            _create_audit(session, obj, "update", as_dict(obj), as_dict(obj))


def _create_audit(session: Session, obj: Any, action: str, old: Dict | None, new: Dict | None) -> None:
    if isinstance(obj, orm.AuditLog) or isinstance(obj, orm.RequestLog):
        return
    model_name = obj.__class__.__name__
    pk_val = getattr(obj, "id", None)
    audit = orm.AuditLog(model=model_name, record_id=str(pk_val), action=action, old_data=old, new_data=new)
    session.add(audit)
    logger.info("audit_event", model=model_name, action=action, record_id=pk_val)


def register_listeners():
    event.listen(Session, "before_flush", before_flush, retval=False)
