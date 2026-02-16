from app.audit.listeners import register_listeners
from app.models.models import Unit
from sqlalchemy import text


def test_audit_inserts(db_session):
    register_listeners()
    unit = Unit(code="bottle", description="Bottle")
    db_session.add(unit)
    db_session.commit()
    audit = db_session.execute(text("select count(1) from audit_log")).scalar()
    assert audit == 1
