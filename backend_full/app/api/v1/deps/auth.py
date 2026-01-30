from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import get_settings
from app.infrastructure.db.session import SessionLocal
from app.models.models import User, Role, Permission, UserRole, RolePermission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
    if user is None:
        raise credentials_exception
    return user


def has_permission(user: User, permission: str, location_id: int | None = None, db: Session | None = None) -> bool:
    """Check if user has a specific permission"""
    # Check if user ID is in super admin IDs
    settings = get_settings()
    # DEBUG: Print super admin IDs and current user ID
    print(f"DEBUG: Current user ID: {user.id}, Super admin IDs: {settings.super_admin_ids}")

    if user.id in settings.super_admin_ids:
        print(f"DEBUG: User {user.id} is a super admin")
        return True

    role_ids = [ur.role_id for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()]
    permissions = (
        db.query(Permission.code, Role.scope, Role.location_id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .filter(Role.id.in_(role_ids))
        .all()
    )
    for code, scope, loc in permissions:
        if code == permission:
            if scope == "global" or loc == location_id:
                return True
    return False


def check_permission(user: User, permission: str, location_id: int | None = None, db: Session | None = None) -> None:
    if not has_permission(user, permission, location_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


class PermissionChecker:
    def __init__(self, permissions: List[str], location_id: Optional[int] = None):
        self.permissions = permissions
        self.location_id = location_id

    def __call__(self, user=Depends(get_current_user), db: Session = Depends(get_db)):
        # Check if user has any of the required permissions
        for perm in self.permissions:
            if has_permission(user, perm, self.location_id, db):
                return user

        raise HTTPException(status_code=403, detail="Permission denied")


def allow_public():
    """Dependency for public endpoints that don't require authentication"""
    pass
