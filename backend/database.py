from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

# Using SQLite for local testing
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_product_catalog.db")

SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    from models import Base
    Base.metadata.create_all(bind=engine)