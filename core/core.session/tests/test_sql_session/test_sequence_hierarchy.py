import pytest
import sqlalchemy
from hypothesis import given

from core.session import BoundSequencePath, PureSequencePath, ExperimentSession
from core.session.result import unwrap
from core.session.sequence_collection import PathIsSequenceError
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)
from ..generate_path import path


def create_empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine, {})

    return session_maker()


@pytest.fixture(scope="function")
def empty_session():
    return create_empty_session()


@given(path)
def test_creation_1(p):
    with create_empty_session() as session:
        bound_path = BoundSequencePath(p, session)
        bound_path.create()
        for ancestor in bound_path.get_ancestors():
            assert session.paths.does_path_exists(ancestor)


def test_creation_2(empty_session):
    with empty_session as session:
        p = BoundSequencePath(r"\a\b\c", session)
        p.create()
        for ancestor in p.get_ancestors():
            assert session.paths.does_path_exists(ancestor)
        p = BoundSequencePath(r"\a\b\d", session)
        p.create()
        for ancestor in p.get_ancestors():
            assert session.paths.does_path_exists(ancestor)


def test_children_1(empty_session):
    with empty_session as session:
        p = BoundSequencePath(r"\a\b\c", session)
        p.create()
        assert p.parent.get_children() == {p}
        p1 = BoundSequencePath(r"\a\b\d", session)
        p1.create()
        assert p.parent.get_children() == {p, p1}
        root_children = BoundSequencePath("\\", session).get_children()
        print(root_children)
        assert root_children == {p.parent.parent}, repr(root_children)


def test_children_2(empty_session):
    with empty_session as session:
        p = BoundSequencePath(r"\a\b\c", session)
        p.create()
        p1 = BoundSequencePath(r"\u\v\w", session)
        p1.create()
        root_children = BoundSequencePath("\\", session).get_children()
        assert root_children == {p.parent.parent, p1.parent.parent}, repr(root_children)


def test_deletion_1(empty_session):
    with empty_session as session:
        p = BoundSequencePath(r"\a\b\c", session)
        p.create()
    with empty_session as session:
        p.delete()
        assert not session.paths.does_path_exists(p)
        assert session.paths.does_path_exists(p.parent)


def test_sequence(empty_session):
    with empty_session as session:
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequence_collection.create(p)
        assert sequence.exists()
        assert session.sequence_collection.is_sequence(p)
        with pytest.raises(PathIsSequenceError):
            session.sequence_collection.create(p)

        assert not unwrap(session.sequence_collection.is_sequence(p.parent))


def test_sequence_deletion(empty_session):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequence_collection.create(p)
        with pytest.raises(PathIsSequenceError):
            session.paths.delete_path(p.parent)
        assert sequence.exists()
