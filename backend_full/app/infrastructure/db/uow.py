from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.infrastructure.db.session import SessionLocal


@contextmanager
def unit_of_work() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
