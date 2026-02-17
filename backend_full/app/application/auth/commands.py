from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import User
from app.security.auth import create_access_token, verify_password


@dataclass(frozen=True)
class LoginCommand:
    username: str
    password: str


class LoginHandler:
    def handle(self, command: LoginCommand, uow: AbstractUnitOfWork) -> dict:
        user = uow.session.query(User).filter(User.username == command.username).first()
        if not user or not verify_password(command.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = create_access_token(user.username)
        return {"access_token": token, "token_type": "bearer"}
