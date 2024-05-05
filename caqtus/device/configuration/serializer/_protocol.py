from typing import Protocol

from caqtus.device import DeviceConfiguration
from caqtus.utils.serialization import JSON


class DeviceConfigJSONSerializerProtocol(Protocol):
    def dump_device_configuration(
        self, config: DeviceConfiguration
    ) -> tuple[str, JSON]: ...

    def load_device_configuration(
        self, tag: str, content: JSON
    ) -> DeviceConfiguration: ...
