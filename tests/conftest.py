import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

import aquen.models  # noqa: F401  (register tables)
from aquen.db import init_db


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as sess:
        yield sess
