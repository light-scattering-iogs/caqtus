import sqlalchemy

from core.session import ExperimentSessionMaker
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
    default_serializer,
)

from typing import Any

import attrs
import pytest
import sqlalchemy
from core.device import DeviceConfigurationAttrs, DeviceParameter
from core.session import ExperimentSession
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
    default_serializer,
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


def get_session_maker() -> ExperimentSessionMaker:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(
        engine,
        {"DummyConfiguration": {"dumper": dump, "loader": load}},
        serializer=default_serializer,
    )
    return session_maker

