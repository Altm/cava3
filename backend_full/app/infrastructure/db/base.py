import re
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Declarative base with naming conventions."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        name = cls.__name__
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        return snake

    @declared_attr.directive
    def __table_args__(cls):
        return {"comment": f"{cls.__name__} table"}
