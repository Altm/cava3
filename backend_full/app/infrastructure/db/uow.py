from __future__ import annotations

from contextlib import contextmanager
from typing import Callable

from sqlalchemy.orm import Session

from app.application.common.uow import AbstractUnitOfWork
from app.infrastructure.db.session import SessionLocal


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        return self

    def commit(self) -> None:
        if self.session is None:
            return
        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            return
        self.session.rollback()

    def close(self) -> None:
        if self.session is None:
            return
        self.session.close()
        self.session = None


class BoundSessionUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: Session):
        self.session = session

    def __enter__(self) -> "BoundSessionUnitOfWork":
        return self

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        return None


@contextmanager
def unit_of_work() -> Session:
    with SqlAlchemyUnitOfWork() as uow:
        try:
            yield uow.session
            uow.commit()
        except Exception:
            uow.rollback()
            raise
