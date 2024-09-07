import datetime

import numpy as np
import pytest
from hypothesis import given, HealthCheck, settings

from caqtus.device import DeviceName
from caqtus.session import (
    PathIsSequenceError,
    DataNotFoundError,
    PathNotFoundError,
)
from caqtus.session import PureSequencePath, Sequence, State
from caqtus.session._result import unwrap
from caqtus.types.data import DataLabel
from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
)
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.units import ureg
from caqtus.types.variable_name import DottedVariableName, VariableName
from .device_configuration import DummyConfiguration
from ..generate_path import path


def test_2(session_maker):
    with session_maker() as session:
        path = PureSequencePath.from_parts(["0", "0"])
        session.paths.create_path(path).unwrap()
        for ancestor in path.get_ancestors():
            assert session.paths.does_path_exists(ancestor)


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
        created_paths = session.paths.create_path(p).unwrap()
        for ancestor in p.get_ancestors():
            assert session.paths.does_path_exists(ancestor)
        for created_path in reversed(created_paths):
            session.paths.delete_path(created_path)


def test_creation_2(session_maker):
    with session_maker() as session:
        p = PureSequencePath(r"\a\b\c")
        session.paths.create_path(p).unwrap()
        for ancestor in p.get_ancestors():
            assert session.paths.does_path_exists(ancestor)
        p = PureSequencePath(r"\a\b\d")
        session.paths.create_path(p).unwrap()
        for ancestor in p.get_ancestors():
            assert session.paths.does_path_exists(ancestor)


def test_root_creation(session_maker):
    with session_maker() as session:
        p = PureSequencePath.root()
        created = session.paths.create_path(p).unwrap()
        assert created == []


def test_children_1(session_maker):
    with session_maker() as session:
        p = PureSequencePath(r"\a\b\c")
        assert p.parent is not None
        session.paths.create_path(p).unwrap()
        assert session.paths.get_children(p.parent).unwrap() == {p}
        p1 = PureSequencePath(r"\a\b\d")
        session.paths.create_path(p1).unwrap()
        assert session.paths.get_children(p.parent).unwrap() == {p, p1}
        root_children = session.paths.get_children(PureSequencePath.root()).unwrap()
        assert root_children == {p.parent.parent}, repr(root_children)


def test_children_2(session_maker):
    with session_maker() as session:
        p = PureSequencePath(r"\a\b\c")
        assert p.parent is not None
        session.paths.create_path(p).unwrap()
        p1 = PureSequencePath(r"\u\v\w")
        assert p1.parent is not None
        session.paths.create_path(p1).unwrap()
        root_children = session.paths.get_children(PureSequencePath.root()).unwrap()
        assert root_children == {p.parent.parent, p1.parent.parent}, repr(root_children)


def test_deletion_1(session_maker):
    with session_maker() as session:
        p = PureSequencePath(r"\a\b\c")
        session.paths.create_path(p)
    with session_maker() as session:
        session.paths.delete_path(p)
        assert not session.paths.does_path_exists(p)
        assert session.paths.does_path_exists(p.parent)


def test_sequence(session_maker, steps_configuration: StepsConfiguration, time_lanes):
    with session_maker() as session:
        p = PureSequencePath(r"\a\b\c")
        session.sequences.create(p, steps_configuration, time_lanes)
        assert session.sequences.is_sequence(p).unwrap()
        with pytest.raises(PathIsSequenceError):
            session.sequences.create(p, steps_configuration, time_lanes)

        assert not session.sequences.is_sequence(p.parent).unwrap()


def test_sequence_deletion(
    session_maker, steps_configuration: StepsConfiguration, time_lanes
):
    with session_maker() as session:
        p = PureSequencePath(r"\test\test")
        session.sequences.create(p, steps_configuration, time_lanes)
        with pytest.raises(PathIsSequenceError):
            session.paths.delete_path(p.parent)
        assert session.sequences.is_sequence(p)


def test_sequence_deletion_1(
    session_maker, steps_configuration: StepsConfiguration, time_lanes
):
    # This test checks mostly that foreign keys are set up correctly.
    # If a sequence path is deleted, it should delete all sequence information and
    # creating a new sequence with the same path should work.
    # Otherwise, the sequence information would be orphaned and creating a new sequence
    # with the same path would fail.
    with session_maker() as session:
        p = PureSequencePath(r"\test")
        session.sequences.create(p, steps_configuration, time_lanes)
        assert session.sequences.is_sequence(p).unwrap()
    with session_maker() as session:
        session.paths.delete_path(p, delete_sequences=True)
        with pytest.raises(PathNotFoundError):
            session.sequences.is_sequence(p).unwrap()
    with session_maker() as session:
        session.sequences.create(p, steps_configuration, time_lanes)
        assert session.sequences.is_sequence(p)


def test_iteration_save(
    session_maker, steps_configuration: StepsConfiguration, time_lanes
):
    with session_maker() as session:
        p = PureSequencePath(r"\test\test")
        sequence = Sequence.create(p, steps_configuration, time_lanes, session)
        assert sequence.get_iteration_configuration() == steps_configuration
        new_steps_configuration = StepsConfiguration(
            steps=steps_configuration.steps + [steps_configuration.steps[0]]
        )
        session.sequences.set_iteration_configuration(
            sequence.path, new_steps_configuration
        )
        session.sequences.set_iteration_configuration(
            sequence.path, new_steps_configuration
        )
        assert sequence.get_iteration_configuration() == new_steps_configuration
        assert sequence.get_time_lanes() == time_lanes


def test_start_date(session_maker, steps_configuration: StepsConfiguration, time_lanes):
    with session_maker() as session:
        p = PureSequencePath(r"\test\test")
        session.sequences.create(p, steps_configuration, time_lanes)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_state(p, State.RUNNING)
    with session_maker() as session:
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
    session_maker, steps_configuration: StepsConfiguration, time_lanes
):
    with session_maker() as session:
        p = PureSequencePath(r"\test")
        sequence = Sequence.create(p, steps_configuration, time_lanes, session)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_state(p, State.RUNNING)
        parameters = {
            DottedVariableName("test"): 1.0,
            DottedVariableName("test2"): 2.0 * ureg.MHz,
        }
        data = {
            DataLabel("a"): [1, 2, 3],
            DataLabel("b"): np.linspace(0, 1, 100),
            DataLabel("c"): np.random.default_rng().normal(size=(10, 20)),
        }
        session.sequences.create_shot(
            p,
            0,
            parameters,
            data,
            datetime.datetime.now(),
            datetime.datetime.now(),
        )
        shots = list(sequence.get_shots())
        assert len(shots) == 1
        assert shots[0].index == 0
        assert shots[0].get_parameters() == parameters
        d = shots[0].get_data()
        assert d[DataLabel("a")] == [1, 2, 3]
        b = d[DataLabel("b")]
        assert isinstance(b, np.ndarray)
        assert np.array_equal(b, np.linspace(0, 1, 100))
        c = d[DataLabel("c")]
        assert isinstance(c, np.ndarray)
        assert np.array_equal(c, data[DataLabel("c")])
        assert shots[0].get_data_by_label(DataLabel("a")) == [1, 2, 3]

        with pytest.raises(DataNotFoundError):
            shots[0].get_data_by_label(DataLabel("d"))


def test_data_not_existing(
    session_maker, steps_configuration: StepsConfiguration, time_lanes
):
    with session_maker() as session:
        p = PureSequencePath(r"\test")
        sequence = Sequence.create(p, steps_configuration, time_lanes, session)
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
        shots = list(sequence.get_shots())
        with pytest.raises(DataNotFoundError):
            shots[0].get_data_by_label(DataLabel("c"))


def test_0(session_maker, steps_configuration: StepsConfiguration, time_lanes):
    with session_maker() as session:
        parameters = ParameterNamespace.from_mapping(
            {
                VariableName("test"): {DottedVariableName("a"): Expression("1")},
            }
        )
        device_configurations = {
            DeviceName("device"): DummyConfiguration(a=1, b="test", remote_server=None),
        }
        p = PureSequencePath(r"\a\b\c")
        Sequence.create(p, steps_configuration, time_lanes, session)

        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_global_parameters(p, parameters)
        session.sequences.set_device_configurations(p, device_configurations)

    with session_maker() as session:
        sequence = Sequence(p, session)
        s = sequence.get_global_parameters()
        d = session.sequences.get_device_configurations(p)
    assert s == parameters
    assert d == device_configurations


def test_1(session_maker, steps_configuration: StepsConfiguration, time_lanes):
    with session_maker() as session:
        configurations = {
            DeviceName("device"): DummyConfiguration(a=1, b="test", remote_server=None)
        }
        p = PureSequencePath(r"\a\b\c")
        Sequence.create(p, steps_configuration, time_lanes, session)
        session.sequences.set_state(p, State.PREPARING)
        session.sequences.set_device_configurations(p, configurations)

    with session_maker() as session:
        sequence = Sequence(p, session)
        d = sequence.get_device_configurations()
    assert d == configurations
