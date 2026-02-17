from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import User
from app.security.auth import get_password_hash


@dataclass(frozen=True)
class CreateUserCommand:
    payload: dict


class CreateUserHandler:
    def handle(self, command: CreateUserCommand, uow: AbstractUnitOfWork) -> dict:
        payload = command.payload
        db = uow.session
        if db.query(User).filter_by(username=payload["username"]).first():
            raise HTTPException(status_code=400, detail="Exists")
        new_user = User(
            username=payload["username"],
            password_hash=get_password_hash(payload["password"]),
            is_active=True,
            is_superuser=payload.get("is_superuser", False),
        )
        db.add(new_user)
        db.flush()
        return {"id": new_user.id, "username": new_user.username}
