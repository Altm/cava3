from __future__ import annotations

from dataclasses import dataclass

from app.application.common.uow import AbstractUnitOfWork
from app.config import get_settings
from app.models.models import Permission, Role, RolePermission, User, UserRole


@dataclass(frozen=True)
class GetCurrentUserInfoQuery:
    user_id: int
    username: str
    is_superuser: bool


class GetCurrentUserInfoHandler:
    def handle(self, query: GetCurrentUserInfoQuery, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        settings = get_settings()
        if query.user_id in settings.super_admin_ids:
            permissions = ["*"]
        else:
            role_ids = [ur.role_id for ur in db.query(UserRole).filter(UserRole.user_id == query.user_id).all()]
            permission_rows = (
                db.query(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .filter(Role.id.in_(role_ids))
                .distinct()
                .all()
            )
            permissions = [perm[0] for perm in permission_rows]

        return {
            "id": query.user_id,
            "username": query.username,
            "is_superuser": query.is_superuser,
            "permissions": permissions,
        }
