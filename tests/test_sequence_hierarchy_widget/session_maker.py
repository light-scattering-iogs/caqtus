import pytest

from caqtus.session.sql import (
    SQLExperimentSessionMaker,
)


@pytest.fixture(scope="function")
def session_maker(tmp_path) -> SQLExperimentSessionMaker:
    url = f"sqlite:///{tmp_path / 'database.db'}"

    session_maker = SQLExperimentSessionMaker.from_url(
        url,
    )
    session_maker.create_tables()
    return session_maker
