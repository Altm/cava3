from typing import Callable

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.v1.deps.uow import get_uow_factory
from app.application.auth.commands import LoginCommand, LoginHandler
from app.application.common import dispatch_command
from app.application.common.uow import AbstractUnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Выдаёт access token по username/password."""
    return dispatch_command(
        uow_factory,
        LoginHandler(),
        LoginCommand(username=form_data.username, password=form_data.password),
    )
