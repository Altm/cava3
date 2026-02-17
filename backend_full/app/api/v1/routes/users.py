from typing import Callable

from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.users.commands import CreateUserCommand, CreateUserHandler
from app.application.users.queries import ListUsersHandler, ListUsersQuery

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def create_user(
    payload: dict,
    user=Depends(PermissionChecker(["user.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт пользователя с ролями и правами по payload."""
    return dispatch_command(uow_factory, CreateUserHandler(), CreateUserCommand(payload=payload))


@router.get("")
def list_users(
    user=Depends(PermissionChecker(["user.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список пользователей системы."""
    return dispatch_query(uow_factory, ListUsersHandler(), ListUsersQuery())
