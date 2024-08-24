import pytest

from caqtus.session.sql._serializer import Serializer
from caqtus.session.sql._session_maker import (
    SQLExperimentSessionMaker,
    SQLiteExperimentSessionMaker,
)


@pytest.fixture(scope="function")
def session_maker(tmp_path) -> SQLExperimentSessionMaker:
    session_maker = SQLiteExperimentSessionMaker(
        path=str(tmp_path / "database.db"),
        serializer=Serializer.default(),
    )
    session_maker.create_tables()
    return session_maker
