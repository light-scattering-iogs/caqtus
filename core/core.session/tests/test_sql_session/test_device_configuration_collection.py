from typing import Any

import attrs
import pytest
import sqlalchemy

from core.device import DeviceConfigurationAttrs, DeviceParameter
from core.session import ExperimentSession
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)
from util import serialization
from util.serialization import JSON


@attrs.define
class DummyConfiguration(DeviceConfigurationAttrs):
    """Dummy configuration to test the device configuration collection."""

    a: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    b: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)

    def get_device_type(self) -> str:
        return "Dummy"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            DeviceParameter("a"): self.a,
            DeviceParameter("b"): self.b,
        }


def dump(configuration: DummyConfiguration) -> JSON:
    return serialization.unstructure(configuration)


def load(configuration: JSON) -> DummyConfiguration:
    return serialization.structure(configuration, DummyConfiguration)


def create_empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(
        engine,
        {"DummyConfiguration": {"dumper": dump, "loader": load}},
    )
    return session_maker()


@pytest.fixture(scope="function")
def empty_session():
    return create_empty_session()


def test_1(empty_session):
    config = DummyConfiguration(
        a=1,
        b="test",
    )
    with empty_session as session:
        session.device_configurations["test"] = config

        config_1 = session.device_configurations["test"]
        assert config_1 == config

        session.device_configurations["test"] = config

        del session.device_configurations["test"]
        with pytest.raises(KeyError):
            session.device_configurations["test"]
