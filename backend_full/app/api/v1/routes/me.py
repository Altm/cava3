from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_current_user, PermissionChecker, get_db
from app.models.models import User, UserRole, RolePermission, Role, Permission

router = APIRouter(prefix="/me", tags=["me"])


def get_user_permissions(user: User, db: Session):
    """Get all permissions for a user"""
    # Superuser has all permissions - return a special marker
    #if user.is_superuser:
    #    return ["*"]

    # Check if user ID is in super admin IDs
    from app.config import get_settings
    settings = get_settings()
    if user.id in settings.super_admin_ids:
        return ["*"]

    # Get user's roles
    role_ids = [ur.role_id for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()]

    # Get permissions for those roles
    permissions = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .filter(Role.id.in_(role_ids))
        .distinct()
        .all()
    )

    return [perm[0] for perm in permissions]


@router.get("")
def get_current_user_info(user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Get user permissions
    permissions = get_user_permissions(user, db)

    return {
        "id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser,
        "permissions": permissions
    }