import pytest

from caqtus.session.sql import (
    SQLExperimentSessionMaker,
    SQLiteExperimentSessionMaker,
    Serializer,
)


@pytest.fixture(scope="function")
def session_maker(tmp_path) -> SQLExperimentSessionMaker:
    session_maker = SQLiteExperimentSessionMaker(
        path=str(tmp_path / "database.db"),
        serializer=Serializer.default(),
    )
    session_maker.create_tables()
    return session_maker
