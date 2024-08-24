import attrs
import pytest

from caqtus.device import DeviceConfiguration
from caqtus.session.sql._serializer import Serializer
from caqtus.session.sql._session_maker import (
    SQLExperimentSessionMaker,
    SQLiteExperimentSessionMaker,
)
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON


@attrs.define
class DummyConfiguration(DeviceConfiguration):
    """Dummy configuration to test the device configuration collection."""

    a: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    b: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)


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
        path=str(tmp_path / "database.db"),
        serializer=serializer,
    )
    session_maker.create_tables()
    return session_maker
