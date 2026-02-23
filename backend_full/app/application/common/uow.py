from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.orm import Session


class AbstractUnitOfWork(ABC):
    session: Session

    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc:
            self.rollback()
        self.close()

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def collect_event(self, event: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def publish_events(self) -> None:
        raise NotImplementedError
