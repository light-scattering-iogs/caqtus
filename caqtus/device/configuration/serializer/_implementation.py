from collections.abc import Callable

from caqtus.utils.serialization import JSON
from ._protocol import DeviceConfigJSONSerializerProtocol
from .._configuration import DeviceConfiguration


class DeviceConfigJSONSerializer(DeviceConfigJSONSerializerProtocol):
    """Handles serialization of device configurations.

    For each device configuration type to handle, a dumper and a constructor function
    must be registered.
    """

    def __init__(self):
        self.loaders: dict[str, Callable[[JSON], DeviceConfiguration]] = {}
        self.dumpers: dict[str, Callable[[DeviceConfiguration], JSON]] = {}

    def register_device_configuration[
        C: DeviceConfiguration
    ](
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

        # We need to transform the dumper into a function that can handle any device
        # configuration type, not just the one it was registered for.
        self.dumpers[type_name] = wrap_dumper(config_type, dumper)
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


class wrap_dumper[C: DeviceConfiguration]:  # noqa: N801
    """Make a dumper function accept all device configuration types."""

    def __init__(self, config_type: type[C], dumper: Callable[[C], JSON]):
        self.dumper = dumper
        self.config_type = config_type

    def __call__(self, config: DeviceConfiguration) -> JSON:
        if not isinstance(config, self.config_type):
            raise TypeError(f"Expected {self.config_type}, got {type(config)}")
        return self.dumper(config)
