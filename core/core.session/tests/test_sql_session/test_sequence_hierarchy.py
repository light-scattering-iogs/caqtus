import pytest
import sqlalchemy
from hypothesis import given

from core.session import BoundSequencePath
from core.session import ExperimentSession
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)
from ..generate_path import path


def create_empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    # url = "sqlite:///database.db"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine)

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
            assert session.sequence_hierarchy.does_path_exists(ancestor)


def test_creation_2(empty_session):
    with empty_session as session:
        p = BoundSequencePath(r"\a\b\c", session)
        p.create()
        for ancestor in p.get_ancestors():
            assert session.sequence_hierarchy.does_path_exists(ancestor)
        p = BoundSequencePath(r"\a\b\d", session)
        p.create()
        for ancestor in p.get_ancestors():
            assert session.sequence_hierarchy.does_path_exists(ancestor)


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
        assert not session.sequence_hierarchy.does_path_exists(p)
        assert session.sequence_hierarchy.does_path_exists(p.parent)


#
# def test_path(empty_session: ExperimentSession):
#     session = empty_session
#
#     with session:
#         path = SequencePath("a.b.c")
#         assert not session.sequence_hierarchy.does_path_exists(path)
#
#         with pytest.raises(PathNotFoundError):
#             unwrap(session.sequence_hierarchy.is_sequence_path(path))
#         path.create(session)
#         for parent in path.get_ancestors(strict=False):
#             assert session.sequence_hierarchy.does_path_exists(parent)
#             assert not session.sequence_hierarchy.is_sequence_path(parent).unwrap()
#
#
# def test_deletion(empty_session: ExperimentSession):
#     session = empty_session
#
#     with session:
#         path = SequencePath("a.b.c")
#         path.create(session)
#         session.sequence_hierarchy.delete_path(SequencePath("a.b"))
#         assert not session.sequence_hierarchy.does_path_exists(path)
