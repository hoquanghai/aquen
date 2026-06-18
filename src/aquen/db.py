from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine

from aquen.config import get_settings


def make_engine(url: str | None = None) -> Engine:
    if url is None:
        url = f"sqlite:///{get_settings().db_path}"
    return create_engine(url, echo=False)


def init_db(engine: Engine) -> None:
    import aquen.models  # noqa: F401  (ensure tables registered)

    SQLModel.metadata.create_all(engine)


def get_session(engine: Engine) -> Session:
    return Session(engine)
