import pytest
from hypothesis import given

from core.session import BoundSequencePath, PureSequencePath, ExperimentSession
from core.session.result import unwrap
from core.session.sequence.iteration_configuration import StepsConfiguration
from core.session.sequence_collection import PathIsSequenceError
from .session_maker import get_session_maker
from ..generate_path import path
from ..steps_iteration import steps_configuration


def create_empty_session() -> ExperimentSession:
    return get_session_maker()()


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


def test_sequence(empty_session, steps_configuration: StepsConfiguration):
    with empty_session as session:
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequence_collection.create(p, steps_configuration)
        assert sequence.exists()
        assert session.sequence_collection.is_sequence(p)
        with pytest.raises(PathIsSequenceError):
            session.sequence_collection.create(p, steps_configuration)

        assert not unwrap(session.sequence_collection.is_sequence(p.parent))


def test_sequence_deletion(empty_session, steps_configuration: StepsConfiguration):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequence_collection.create(p, steps_configuration)
        with pytest.raises(PathIsSequenceError):
            session.paths.delete_path(p.parent)
        assert sequence.exists()


def test_iteration_save(empty_session, steps_configuration: StepsConfiguration):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequence_collection.create(p, steps_configuration)
        assert sequence.get_iteration_configuration() == steps_configuration
        new_steps_configuration = StepsConfiguration(
            steps=steps_configuration.steps + [steps_configuration.steps[0]]
        )
        sequence.set_iteration_configuration(new_steps_configuration)
        assert sequence.get_iteration_configuration() == new_steps_configuration
        assert (
            session.sequence_collection.get_iteration_configuration(sequence)
            == new_steps_configuration
        )
