from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session

T = TypeVar("T")


class Repository(Generic[T]):
    """Generic repository for ORM models."""

    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    def get(self, id) -> Optional[T]:
        return self.db.get(self.model, id)

    def list(self) -> List[T]:
        return self.db.query(self.model).all()

    def add(self, obj: T) -> T:
        self.db.add(obj)
        return obj
