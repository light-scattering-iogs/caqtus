from typing import Any, Mapping

import attrs
import pytest

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.session.sql import (
    SQLExperimentSessionMaker,
    Serializer,
    SQLiteExperimentSessionMaker,
)
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON


@attrs.define
class DummyConfiguration(DeviceConfiguration):
    """Dummy configuration to test the device configuration collection."""

    a: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    b: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)

    def get_device_initialization_method(self, device_name, sequence_context):
        return super().get_device_initialization_method(device_name, sequence_context)

    def compile_device_shot_parameters(
        self, device_name: DeviceName, shot_context
    ) -> Mapping[str, Any]:
        pass


def dump(configuration: DummyConfiguration) -> JSON:
    return serialization.unstructure(configuration)


def load(configuration: JSON) -> DummyConfiguration:
    return serialization.structure(configuration, DummyConfiguration)


@pytest.fixture(scope="function")
def session_maker(tmp_path) -> SQLExperimentSessionMaker:
    # url = f"sqlite:///{tmp_path / 'database.db'}"

    serializer = Serializer.default()
    serializer.register_device_configuration(DummyConfiguration, dump, load)

    session_maker = SQLiteExperimentSessionMaker(
        str(tmp_path / "database.db"),
        serializer=serializer,
    )
    session_maker.create_tables()
    return session_maker
