from collections.abc import Generator

import pytest
from pytest_postgresql import factories

from caqtus.extension import Experiment
from caqtus.session import (
    PureSequencePath,
    ExperimentSession,
    ExperimentSessionMaker,
    PathIsSequenceError,
    PathNotFoundError,
    SequenceStateError,
    State,
)
from caqtus.session._copy import copy_path
from caqtus.types.parameter import ParameterNamespace
from caqtus.utils.result import unwrap, is_failure_type, is_success
from tests.conftest import initialize, to_postgresql_config
from tests.test_session.test_sql.device_configuration import DummyConfiguration

postgresql_destination_no_proc = factories.postgresql_noproc(
    load=[initialize], dbname="caqtus_test_destination"
)

postgresql_destination = factories.postgresql("postgresql_destination_no_proc")


@pytest.fixture
def destination_session_maker(postgresql_destination) -> ExperimentSessionMaker:
    exp = Experiment()
    exp.configure_storage(to_postgresql_config(postgresql_destination))
    exp._extension.device_configurations_serializer.register_device_configuration(
        DummyConfiguration, DummyConfiguration.dump, DummyConfiguration.load
    )
    return exp._get_session_maker(check_schema=False)


@pytest.fixture
def source_session(session_maker) -> Generator[ExperimentSession, None, None]:
    with session_maker.session() as session:
        yield session


@pytest.fixture
def destination_session(
    destination_session_maker,
) -> Generator[ExperimentSession, None, None]:
    with destination_session_maker.session() as session:
        yield session


def test_destination_path_is_sequence(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
    steps_configuration,
    time_lanes,
):
    path = PureSequencePath.root() / "path"
    unwrap(destination_session.sequences.create(path, steps_configuration, time_lanes))
    result = copy_path(path, source_session, destination_session)
    assert is_failure_type(result, PathIsSequenceError)


def test_copy_not_existing_path(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
):
    path = PureSequencePath.root() / "path"
    result = copy_path(path, source_session, destination_session)
    assert is_failure_type(result, PathNotFoundError)


def test_creation_date_is_copied(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
):
    path = PureSequencePath.root() / "path"
    unwrap(source_session.paths.create_path(path))
    result = copy_path(path, source_session, destination_session)
    assert is_success(result)
    assert unwrap(source_session.paths.get_path_creation_date(path)) == unwrap(
        destination_session.paths.get_path_creation_date(path)
    )


def test_copy_not_existing_file(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
):
    path = PureSequencePath.root() / "path"
    destination_session.paths.create_path(path)
    result = copy_path(path, source_session, destination_session)
    assert is_failure_type(result, PathNotFoundError)


def test_children_are_copied(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
):
    parent = PureSequencePath.root() / "parent"
    unwrap(source_session.paths.create_path(parent))
    child_path = parent / "child"
    unwrap(source_session.paths.create_path(child_path))
    result = copy_path(parent, source_session, destination_session)
    assert is_success(result)
    assert destination_session.paths.does_path_exists(child_path)


def test_cant_copy_running_sequence(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
    steps_configuration,
    time_lanes,
):
    path = PureSequencePath.root() / "path"
    unwrap(source_session.sequences.create(path, steps_configuration, time_lanes))
    unwrap(source_session.sequences.set_preparing(path, {}, ParameterNamespace.empty()))
    result = copy_path(path, source_session, destination_session)
    assert is_failure_type(result, SequenceStateError)


def test_copy_draft_sequence(
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
    steps_configuration,
    time_lanes,
):
    path = PureSequencePath.root() / "path"
    unwrap(source_session.sequences.create(path, steps_configuration, time_lanes))
    unwrap(copy_path(path, source_session, destination_session))
    assert unwrap(destination_session.sequences.get_state(path)) == State.DRAFT
    assert (
        destination_session.sequences.get_iteration_configuration(path)
        == steps_configuration
    )
    assert destination_session.sequences.get_time_lanes(path) == time_lanes
