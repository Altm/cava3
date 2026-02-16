from __future__ import annotations

from typing import Callable

from app.application.common.uow import AbstractUnitOfWork
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


def get_uow_factory() -> Callable[[], AbstractUnitOfWork]:
    return SqlAlchemyUnitOfWork
