from __future__ import annotations

import pytest
from pytest_postgresql import factories

from caqtus.extension import Experiment, upgrade_database
from caqtus.session.sql import PostgreSQLConfig, PostgreSQLExperimentSessionMaker
from .device_configuration import DummyConfiguration

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
def session_maker(initialized_database_config) -> PostgreSQLExperimentSessionMaker:
    exp = Experiment()
    exp.configure_storage(initialized_database_config)
    exp._extension.device_configurations_serializer.register_device_configuration(
        DummyConfiguration, DummyConfiguration.dump, DummyConfiguration.load
    )
    return exp._get_session_maker(check_schema=False)
