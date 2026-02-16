from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.application.common.uow import AbstractUnitOfWork
from app.models import models
from app.schemas import simple as schemas


@dataclass(frozen=True)
class ListLocationsQuery:
    pass


@dataclass(frozen=True)
class CreateLocationCommand:
    payload: schemas.LocationBase


class ListLocationsHandler:
    def handle(self, query: ListLocationsQuery, uow: AbstractUnitOfWork) -> List[schemas.Location]:
        db = uow.session
        locations = db.query(models.Location).all()
        return [
            schemas.Location(
                id=l.id,
                name=l.name,
                code=l.code,
            )
            for l in locations
        ]


class CreateLocationHandler:
    def handle(self, command: CreateLocationCommand, uow: AbstractUnitOfWork) -> schemas.Location:
        db = uow.session
        location = command.payload
        db_location = models.Location(name=location.name, code=location.code)
        db.add(db_location)
        db.flush()
        return schemas.Location(
            id=db_location.id,
            name=db_location.name,
            code=db_location.code,
        )
