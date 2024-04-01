import datetime

import numpy as np
import pytest
from hypothesis import given, HealthCheck, settings

from caqtus.device import DeviceName
from caqtus.session import (
    BoundSequencePath,
    PureSequencePath,
    ParameterNamespace,
)
from caqtus.session.result import unwrap
from caqtus.session.sequence import State, Shot
from caqtus.session.sequence.iteration_configuration import (
    StepsConfiguration,
)
from caqtus.session.sequence_collection import PathIsSequenceError
from caqtus.session.shot import TimeLanes
from caqtus.types.data import DataLabel
from caqtus.types.expression import Expression
from caqtus.types.units import ureg
from caqtus.types.variable_name import DottedVariableName, VariableName
from .session_maker import session_maker, DummyConfiguration
from ..generate_path import path
from ..steps_iteration import steps_configuration


@pytest.fixture(scope="function")
def empty_session(session_maker):
    return session_maker()


def test_2(session_maker):
    with session_maker() as session:
        bound_path = BoundSequencePath(PureSequencePath.from_parts(["0", "0"]), session)
        created_paths = bound_path.create()
        for ancestor in bound_path.get_ancestors():
            assert session.paths.does_path_exists(ancestor)
        for created_path in reversed(created_paths):
            created_path.delete()


def test_3(session_maker):
    with session_maker() as session:
        p = PureSequencePath(r"\a\b")
        session.paths.create_path(p)
    with session_maker() as session:
        session.paths.delete_path(p)
    with session_maker() as session:
        session.paths.create_path(p)


@given(p=path)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_creation_1(p, session_maker):
    with session_maker() as session:
        bound_path = BoundSequencePath(p, session)
        created_paths = bound_path.create()
        for ancestor in bound_path.get_ancestors():
            assert session.paths.does_path_exists(ancestor)
        for created_path in reversed(created_paths):
            created_path.delete()


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
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        assert sequence.exists(session)
        assert session.sequences.is_sequence(p)
        with pytest.raises(PathIsSequenceError):
            session.sequences.create(p, steps_configuration, time_lanes)

        assert not unwrap(session.sequences.is_sequence(p.parent))


def test_sequence_deletion(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        with pytest.raises(PathIsSequenceError):
            session.paths.delete_path(p.parent)
        assert sequence.exists(session)


def test_sequence_deletion_1(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    # This test checks mostly that foreign keys are set up correctly.
    # If a sequence path is deleted, it should delete all sequence information and
    # creating a new sequence with the same path should work.
    # Otherwise, the sequence information would be orphaned and creating a new sequence
    # with the same path would fail.
    with empty_session as session:
        p = PureSequencePath(r"\test")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        assert sequence.exists(session)
    with empty_session as session:
        session.paths.delete_path(p, delete_sequences=True)
        assert not sequence.exists(session)
    with empty_session as session:
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        assert sequence.exists(session)


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
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        assert sequence.get_iteration_configuration(session) == steps_configuration
        new_steps_configuration = StepsConfiguration(
            steps=steps_configuration.steps + [steps_configuration.steps[0]]
        )
        session.sequences.set_iteration_configuration(sequence, new_steps_configuration)
        session.sequences.set_iteration_configuration(sequence, new_steps_configuration)
        assert sequence.get_iteration_configuration(session) == new_steps_configuration
        assert sequence.get_time_lanes(session) == time_lanes


def test_start_date(empty_session, steps_configuration: StepsConfiguration, time_lanes):
    with empty_session as session:
        p = PureSequencePath(r"\test\test")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_state(p, State.RUNNING)
    with session:
        stats = unwrap(session.sequences.get_stats(p))
        d = stats.start_time
        assert d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        assert (
            now - datetime.timedelta(seconds=10)
            < d
            < now + datetime.timedelta(seconds=10)
        )


def test_shot_creation(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    with empty_session as session:
        p = PureSequencePath(r"\test")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_state(p, State.RUNNING)
        parameters = {
            DottedVariableName("test"): 1.0,
            DottedVariableName("test2"): 2.0 * ureg.MHz,
        }
        data = {
            DataLabel("a"): [1, 2, 3],
            DataLabel("b"): np.linspace(0, 1, 100),
            DataLabel("c"): np.random.normal(size=(10, 20)),
        }
        session.sequences.create_shot(
            p,
            0,
            parameters,
            data,
            datetime.datetime.now(),
            datetime.datetime.now(),
        )
        shots = sequence.get_shots(session)
        assert shots == [Shot(sequence, 0)], sequence.get_shots(session)
        assert shots[0].get_parameters(session) == parameters
        d = shots[0].get_data(session)
        assert d[DataLabel("a")] == [1, 2, 3]
        assert np.array_equal(d[DataLabel("b")], np.linspace(0, 1, 100))
        assert np.array_equal(d[DataLabel("c")], data[DataLabel("c")])
        assert shots[0].get_data_by_label(DataLabel("a"), session) == [1, 2, 3]

        with pytest.raises(KeyError):
            shots[0].get_data_by_label(DataLabel("d"), session)


def test_data_not_existing(
    empty_session, steps_configuration: StepsConfiguration, time_lanes
):
    with empty_session as session:
        p = PureSequencePath(r"\test")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_state(p, State.RUNNING)
        parameters = {}
        data = {
            DataLabel("a"): [1, 2, 3],
            DataLabel("b"): np.linspace(0, 1, 100),
        }
        session.sequences.create_shot(
            p,
            0,
            parameters,
            data,
            datetime.datetime.now(),
            datetime.datetime.now(),
        )
        shots = sequence.get_shots(session)
        with pytest.raises(KeyError):
            shots[0].get_data_by_label(DataLabel("c"), session)


def test_0(empty_session, steps_configuration: StepsConfiguration, time_lanes):
    with empty_session as session:
        parameters = ParameterNamespace.from_mapping(
            {
                VariableName("test"): {DottedVariableName("a"): Expression("1")},
            }
        )
        device_configurations = {
            DeviceName("device"): DummyConfiguration(
                a=1, b="test", remote_server="test"
            ),
        }
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)

        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_global_parameters(p, parameters)
        session.sequences.set_device_configurations(p, device_configurations)

    with session:
        s = sequence.get_global_parameters(session)
        d = session.sequences.get_device_configurations(p)
    assert s == parameters
    assert d == device_configurations


def test_1(empty_session, steps_configuration: StepsConfiguration, time_lanes):
    with empty_session as session:
        configurations = {
            DeviceName("device"): DummyConfiguration(
                a=1, b="test", remote_server="test"
            )
        }
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_device_configurations(p, configurations)

    with session:
        d = sequence.get_device_configurations(session)
    assert d == configurations
