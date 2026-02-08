# app/database.py — Conexão SQLite e sessão
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_db_file = (_PROJECT_ROOT / "ml_intelligence.db").as_posix()
_DB_PATH = os.getenv("DATABASE_URL", f"sqlite:///{_db_file}")

engine = create_engine(_DB_PATH, connect_args={"check_same_thread": False} if "sqlite" in _DB_PATH else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para obter sessão do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria as tabelas se não existirem."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
