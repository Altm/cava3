from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import User
from app.schemas.users import UserCreateIn
from app.security.auth import get_password_hash


@dataclass(frozen=True)
class CreateUserCommand:
    payload: UserCreateIn


class CreateUserHandler:
    def handle(self, command: CreateUserCommand, uow: AbstractUnitOfWork) -> User:
        payload = command.payload
        db = uow.session
        if db.query(User).filter_by(username=payload.username).first():
            raise HTTPException(status_code=400, detail="Exists")
        new_user = User(
            username=payload.username,
            password_hash=get_password_hash(payload.password),
            is_active=bool(payload.is_active),
            is_superuser=bool(payload.is_superuser),
        )
        db.add(new_user)
        db.flush()
        return new_user
