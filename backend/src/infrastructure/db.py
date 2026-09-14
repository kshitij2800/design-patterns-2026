from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from collections.abc import Generator
from infrastructure.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Shared declarative base — business models will inherit from this."""


def check_db() -> str:
    """Return 'ok' if the database is reachable, 'fail' otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "fail"

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()