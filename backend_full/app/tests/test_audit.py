from app.audit.listeners import register_listeners
from app.models.models import Unit


def test_audit_inserts(db_session):
    register_listeners()
    unit = Unit(code="bottle", description="Bottle")
    db_session.add(unit)
    db_session.commit()
    audit = db_session.execute("select count(1) from auditlog").scalar()
    assert audit == 1
