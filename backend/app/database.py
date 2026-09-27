from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    kwargs: dict = {"pool_pre_ping": True}
    if settings.database_url.startswith("postgresql"):
        kwargs["connect_args"] = {"connect_timeout": 2}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


@lru_cache
def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def reset_database_caches() -> None:
    """Dispose cached database resources before rebuilding them.

    This is used by tests/CLI flows that change DATABASE_URL at runtime.
    Disposing first prevents leaked SQLite/PostgreSQL connections and keeps
    Python from emitting ResourceWarning messages during interpreter shutdown.
    """
    engine = get_engine() if get_engine.cache_info().currsize else None
    get_session_factory.cache_clear()
    if engine is not None:
        engine.dispose()
    get_engine.cache_clear()
