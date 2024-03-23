from typing import Any

import attrs
import sqlalchemy
from caqtus.device import DeviceConfigurationAttrs, DeviceParameter
from caqtus.session import ExperimentSessionMaker
from caqtus.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
    default_sequence_serializer,
    Serializer,
    DeviceConfigurationSerializer,
)
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON


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
        serializer=Serializer(
            device_configuration_serializers={
                "DummyConfiguration": DeviceConfigurationSerializer(
                    dumper=dump, loader=load
                )
            },
            sequence_serializer=default_sequence_serializer,
        ),
    )
    return session_maker
