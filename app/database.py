# app/database.py — Conexão ao banco (SQLite local / PostgreSQL produção)
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_db_file = (_PROJECT_ROOT / "ml_intelligence.db").as_posix()

# Produção: use DATABASE_URL (PostgreSQL) para persistência entre deploys.
# SQLite no servidor é apagado a cada deploy (filesystem efêmero).
_raw_url = os.getenv("DATABASE_URL", f"sqlite:///{_db_file}")
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

_DB_PATH = _raw_url
_connect_args = {}
if "sqlite" in _DB_PATH:
    _connect_args["check_same_thread"] = False

# SQLAlchemy exige connect_args como dict; None causa TypeError no create_engine
engine = create_engine(_DB_PATH, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para obter sessão do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_add_telegram_chat_id():
    """Adiciona coluna telegram_chat_id em users se não existir (migração)."""
    try:
        with engine.connect() as conn:
            if "sqlite" in _DB_PATH:
                conn.execute(text("ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(64)"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(64)"))
            conn.commit()
    except Exception as e:
        msg = str(e).lower()
        if "duplicate column" in msg or "already exists" in msg:
            pass
        else:
            raise


def init_db():
    """Cria as tabelas se não existirem. Em produção use DATABASE_URL (PostgreSQL) para persistir dados."""
    import logging
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    try:
        _migrate_add_telegram_chat_id()
    except Exception:
        pass
    kind = "SQLite (dados locais)" if "sqlite" in _DB_PATH else "PostgreSQL (persistente)"
    logging.getLogger("ml-intelligence").info("Banco: %s", kind)
