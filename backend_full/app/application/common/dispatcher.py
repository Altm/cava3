from __future__ import annotations

from typing import Callable, Protocol, TypeVar

from app.application.common.uow import AbstractUnitOfWork


CommandT = TypeVar("CommandT")
QueryT = TypeVar("QueryT")
ResultT = TypeVar("ResultT")


class CommandHandler(Protocol[CommandT, ResultT]):
    def handle(self, command: CommandT, uow: AbstractUnitOfWork) -> ResultT:
        ...


class QueryHandler(Protocol[QueryT, ResultT]):
    def handle(self, query: QueryT, uow: AbstractUnitOfWork) -> ResultT:
        ...


def dispatch_command(
    uow_factory: Callable[[], AbstractUnitOfWork],
    handler: CommandHandler[CommandT, ResultT],
    command: CommandT,
) -> ResultT:
    with uow_factory() as uow:
        result = handler.handle(command, uow)
        uow.commit()
        return result


def dispatch_query(
    uow_factory: Callable[[], AbstractUnitOfWork],
    handler: QueryHandler[QueryT, ResultT],
    query: QueryT,
) -> ResultT:
    with uow_factory() as uow:
        return handler.handle(query, uow)
