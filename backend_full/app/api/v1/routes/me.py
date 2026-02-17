from typing import Callable

from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import get_current_user
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.me.queries import GetCurrentUserInfoHandler, GetCurrentUserInfoQuery

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def get_current_user_info(
    user=Depends(get_current_user),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает профиль текущего авторизованного пользователя."""
    return dispatch_query(
        uow_factory,
        GetCurrentUserInfoHandler(),
        GetCurrentUserInfoQuery(user_id=user.id, username=user.username, is_superuser=user.is_superuser),
    )
