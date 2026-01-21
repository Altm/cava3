from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Declarative base with naming conventions."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @declared_attr.directive
    def __table_args__(cls):
        return {"comment": f"{cls.__name__} table"}
