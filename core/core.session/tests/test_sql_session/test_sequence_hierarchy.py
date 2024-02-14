import datetime

import numpy as np
import pytest
from hypothesis import given

from core.device import DeviceName
from core.session import BoundSequencePath, PureSequencePath, ExperimentSession
from core.session.result import unwrap
from core.session.sequence import State, Shot
from core.session.sequence.iteration_configuration import StepsConfiguration
from core.session.sequence_collection import PathIsSequenceError
from core.session.shot import TimeLanes
from core.types.data import DataLabel
from core.types.expression import Expression
from core.types.units import ureg
from core.types.variable_name import DottedVariableName
from .session_maker import get_session_maker, DummyConfiguration
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
        table_uuid = session.constants.add_table("test", [])
        device_uuid = session.device_configurations.add_device_configuration(
            "device", DummyConfiguration(a=1, b="test", remote_server="test")
        )
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)

        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_constant_table_uuids(p, {table_uuid})
        session.sequences.set_device_configuration_uuids(p, {device_uuid})

    with session:
        s = session.sequences.get_constant_table_uuids(p)
        d = session.sequences.get_device_configuration_uuids(p)
    assert s == {table_uuid}
    assert d == {device_uuid}


def test_1(empty_session, steps_configuration: StepsConfiguration, time_lanes):
    with empty_session as session:
        configurations = {
            DeviceName("device"): DummyConfiguration(
                a=1, b="test", remote_server="test"
            )
        }
        p = PureSequencePath(r"\a\b\c")
        sequence = session.sequences.create(p, steps_configuration, time_lanes)
        session.sequences.set_device_configurations(p, configurations)

    with session:
        d = sequence.get_device_configurations(session)
    assert d == configurations
