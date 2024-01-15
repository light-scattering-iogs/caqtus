import datetime

import pytest
from hypothesis import given

from core.session import BoundSequencePath, PureSequencePath, ExperimentSession
from core.session.result import unwrap
from core.session.sequence import State, Shot
from core.session.sequence.iteration_configuration import StepsConfiguration
from core.session.sequence_collection import PathIsSequenceError
from core.session.shot import TimeLanes
from core.types.expression import Expression
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


def test_sequence(empty_session, steps_configuration: StepsConfiguration, time_lanes):
    with empty_session as session:
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequence_collection.create(
            p, steps_configuration, time_lanes
        )
        assert sequence.exists()
        assert session.sequence_collection.is_sequence(p)
        with pytest.raises(PathIsSequenceError):
            session.sequence_collection.create(p, steps_configuration, time_lanes)

        assert not unwrap(session.sequence_collection.is_sequence(p.parent))


def test_sequence_deletion(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequence_collection.create(
            p, steps_configuration, time_lanes
        )
        with pytest.raises(PathIsSequenceError):
            session.paths.delete_path(p.parent)
        assert sequence.exists()


@pytest.fixture
def time_lanes():
    return TimeLanes(
        step_names=["step1", "step2"],
        step_durations=[Expression("1 ms"), Expression("2 ms")],
        lanes={},
    )


def test_iteration_save(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequence_collection.create(
            p, steps_configuration, time_lanes
        )
        assert sequence.get_iteration_configuration() == steps_configuration
        new_steps_configuration = StepsConfiguration(
            steps=steps_configuration.steps + [steps_configuration.steps[0]]
        )
        session.sequence_collection.set_iteration_configuration(
            sequence, new_steps_configuration
        )
        session.sequence_collection.set_iteration_configuration(
            sequence, new_steps_configuration
        )
        assert sequence.get_iteration_configuration() == new_steps_configuration
        assert sequence.get_time_lanes() == time_lanes


def test_shot_creation(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    with empty_session as session:
        p = PureSequencePath(r"\test")
        sequence = session.sequence_collection.create(
            p, steps_configuration, time_lanes
        )
        session.sequence_collection.set_state(p, State.PREPARING)
        session.sequence_collection.set_state(p, State.RUNNING)
        session.sequence_collection.create_shot(
            p, 0, datetime.datetime.now(), datetime.datetime.now()
        )
        assert sequence.get_shots() == [Shot(sequence, 0)], sequence.get_shots()
