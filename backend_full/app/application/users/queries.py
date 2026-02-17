from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import User


@dataclass(frozen=True)
class ListUsersQuery:
    pass


class ListUsersHandler:
    def handle(self, query: ListUsersQuery, uow: AbstractUnitOfWork) -> List[User]:
        return uow.session.query(User).all()
