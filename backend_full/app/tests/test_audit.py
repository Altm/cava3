from app.audit.listeners import register_listeners
from app.audit.context import set_audit_user_id, reset_audit_user_id
from app.models.models import Unit
from sqlalchemy import text


def test_audit_inserts(db_session):
    register_listeners()
    unit = Unit(code="bottle", description="Bottle")
    db_session.add(unit)
    db_session.commit()
    audit = db_session.execute(text("select count(1) from audit_log")).scalar()
    assert audit == 1


def test_audit_stores_actor_user_id(db_session):
    register_listeners()
    token = set_audit_user_id(123)
    try:
        unit = Unit(code="bottle_actor", description="Bottle Actor")
        db_session.add(unit)
        db_session.commit()
    finally:
        reset_audit_user_id(token)

    actor = db_session.execute(
        text("select actor from audit_log where model = 'Unit' and record_id = :rid"),
        {"rid": str(unit.id)},
    ).scalar()
    assert actor == "123"
