from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_database_url


DATABASE_URL = get_database_url()


engine_options = {}
if DATABASE_URL.startswith("sqlite:"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()
