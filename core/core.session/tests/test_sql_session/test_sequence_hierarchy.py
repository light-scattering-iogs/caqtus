import pytest
import sqlalchemy

from core.session import ExperimentSession, SequencePath
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)


@pytest.fixture(scope="function")
def empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine)

    return session_maker()


def test_path(empty_session: ExperimentSession):
    session = empty_session

    with session:
        path = SequencePath("a.b.c")
        assert not session.sequence_hierarchy.does_path_exists(path)
        path.create(session)
        for parent in path.get_ancestors(strict=False):
            assert session.sequence_hierarchy.does_path_exists(parent)
