from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.security.auth import get_password_hash
from app.models.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def create_user(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "user.write", db=db)
    if db.query(User).filter_by(username=payload["username"]).first():
        raise HTTPException(status_code=400, detail="Exists")
    new_user = User(
        username=payload["username"],
        password_hash=get_password_hash(payload["password"]),
        is_active=True,
        is_superuser=payload.get("is_superuser", False),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}


@router.get("")
def list_users(db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "user.read", db=db)
    return db.query(User).all()
