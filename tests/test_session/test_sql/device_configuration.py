from __future__ import annotations

import attrs

from caqtus.device import DeviceConfiguration
from caqtus.utils import serialization


@attrs.define
class DummyConfiguration(DeviceConfiguration):
    """Dummy configuration to test the device configuration collection."""

    a: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    b: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)

    def dump(self):
        return serialization.unstructure(self)

    @classmethod
    def load(cls, configuration) -> DummyConfiguration:
        return serialization.structure(configuration, DummyConfiguration)
