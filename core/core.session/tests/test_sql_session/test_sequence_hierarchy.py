import pytest
import sqlalchemy

from core.session import ExperimentSession, SequencePath
from core.session.sequence import PathNotFoundError
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)
from core.session._return_or_raise import unwrap


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

        with pytest.raises(PathNotFoundError):
            unwrap(session.sequence_hierarchy.is_sequence_path(path))
        path.create(session)
        for parent in path.get_ancestors(strict=False):
            assert session.sequence_hierarchy.does_path_exists(parent)
            assert not session.sequence_hierarchy.is_sequence_path(parent).unwrap()
