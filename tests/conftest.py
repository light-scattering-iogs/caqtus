from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_postgresql import factories

from caqtus.extension import Experiment
from caqtus.extension import upgrade_database
from caqtus.session import PureSequencePath, State, ExperimentSessionMaker
from caqtus.session.sql import PostgreSQLConfig
from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
    ArangeLoop,
)
from caqtus.types.timelane import TimeLanes
from caqtus.types.variable_name import DottedVariableName
from tests.test_session.test_sql.device_configuration import DummyConfiguration


@pytest.fixture
def anyio_backend():
    return "trio"


postgresql_empty_no_proc = factories.postgresql_noproc(dbname="caqtus_test_empty")

postgresql_empty = factories.postgresql("postgresql_empty_no_proc")


def initialize(**kwargs):
    exp = Experiment()
    exp.configure_storage(
        PostgreSQLConfig(
            username=kwargs["user"],
            host=kwargs["host"],
            password=kwargs["password"],
            port=kwargs["port"],
            database=kwargs["dbname"],
        )
    )
    upgrade_database(exp)


postgresql_initialized_no_proc = factories.postgresql_noproc(
    load=[initialize], dbname="caqtus_test_initialized"
)

postgresql_initialized = factories.postgresql("postgresql_initialized_no_proc")


def to_postgresql_config(p) -> PostgreSQLConfig:
    return PostgreSQLConfig(
        username=p.info.user,
        password=p.info.password,
        host=p.info.host,
        port=p.info.port,
        database=p.info.dbname,
    )


@pytest.fixture
def empty_database_config(postgresql_empty) -> PostgreSQLConfig:
    return to_postgresql_config(postgresql_empty)


@pytest.fixture
def initialized_database_config(postgresql_initialized) -> PostgreSQLConfig:
    return to_postgresql_config(postgresql_initialized)


@pytest.fixture
def session_maker(initialized_database_config) -> ExperimentSessionMaker:
    exp = Experiment()
    exp.configure_storage(initialized_database_config)
    exp._extension.device_configurations_serializer.register_device_configuration(
        DummyConfiguration, DummyConfiguration.dump, DummyConfiguration.load
    )
    return exp._get_session_maker(check_schema=False)


@pytest.fixture
def steps_configuration() -> StepsConfiguration:
    step_configuration = StepsConfiguration(
        steps=[
            VariableDeclaration(
                variable=DottedVariableName("a"), value=Expression("1")
            ),
            LinspaceLoop(
                variable=DottedVariableName("b"),
                start=Expression("0"),
                stop=Expression("1"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
            ArangeLoop(
                variable=DottedVariableName("c"),
                start=Expression("0"),
                stop=Expression("1"),
                step=Expression("0.1"),
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
            ExecuteShot(),
        ],
    )
    return step_configuration


@pytest.fixture
def time_lanes() -> TimeLanes:
    return TimeLanes(
        step_names=["step1", "step2"],
        step_durations=[Expression("1 ms"), Expression("2 ms")],
        lanes={},
    )


@pytest.fixture
def draft_sequence(
    session_maker, steps_configuration, time_lanes
) -> Generator[PureSequencePath, None, None]:
    path = PureSequencePath(r"\test")
    with session_maker.session() as session:
        session.sequences.create(path, steps_configuration, time_lanes)
    yield path
    with session_maker.session() as session:
        session.paths.delete_path(path, delete_sequences=True)


@pytest.fixture
def initializing_sequence(session_maker, draft_sequence) -> PureSequencePath:
    with session_maker.session() as session:
        session.sequences.set_state(draft_sequence, State.PREPARING)
    return draft_sequence


@pytest.fixture
def running_sequence(session_maker, initializing_sequence) -> PureSequencePath:
    with session_maker.session() as session:
        session.sequences.set_state(initializing_sequence, State.RUNNING)
    return initializing_sequence


@pytest.fixture
def crashed_sequence(session_maker, running_sequence) -> PureSequencePath:
    with session_maker.session() as session:
        session.sequences.set_state(running_sequence, State.CRASHED)
    return running_sequence
