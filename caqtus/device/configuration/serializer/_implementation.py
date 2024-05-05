from collections.abc import Callable
from typing import TypeVar

from caqtus.utils.serialization import JSON
from ._protocol import DeviceConfigJSONSerializerProtocol
from .._configuration import DeviceConfiguration

C = TypeVar("C", bound=DeviceConfiguration)


class DeviceConfigJSONSerializer(DeviceConfigJSONSerializerProtocol):
    def __init__(self):
        self.loaders: dict[str, Callable[[JSON], DeviceConfiguration]] = {}
        self.dumpers: dict[str, Callable[[DeviceConfiguration], JSON]] = {}

    def register_device_configuration(
        self,
        config_type: type[C],
        dumper: Callable[[C], JSON],
        constructor: Callable[[JSON], C],
    ) -> None:
        """Register a custom device configuration type for serialization.

        Args:
            config_type: A subclass of :class:`DeviceConfiguration` that is being
                registered for serialization.
            dumper: A function that will be called when it is necessary to convert a
                device configuration to JSON format.
            constructor: A function that will be called when it is necessary to build a
                device configuration from the JSON data returned by the dumper.
        """

        type_name = config_type.__qualname__

        self.dumpers[type_name] = dumper
        self.loaders[type_name] = constructor

    def dump_device_configuration(
        self, config: DeviceConfiguration
    ) -> tuple[str, JSON]:
        type_name = type(config).__qualname__
        dumper = self.dumpers[type_name]
        return type_name, dumper(config)

    def load_device_configuration(self, tag: str, content: JSON) -> DeviceConfiguration:
        constructor = self.loaders[tag]
        return constructor(content)
