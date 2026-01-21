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


def check_permission(user: User, permission: str, location_id: int | None = None, db: Session | None = None) -> None:
    if user.is_superuser:
        return
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
                return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
