from typing import Protocol

from caqtus.device.configuration.serializer import DeviceConfigJSONSerializerProtocol
from caqtus.experiment_control.device_manager_extension import (
    DeviceManagerExtensionProtocol,
)
from caqtus.gui.condetrol._extension import CondetrolExtensionProtocol
from caqtus.types.timelane._serializer import TimeLaneSerializerProtocol


class CaqtusExtensionProtocol(Protocol):
    @property
    def condetrol_extension(self) -> CondetrolExtensionProtocol: ...

    @property
    def device_configurations_serializer(
        self,
    ) -> DeviceConfigJSONSerializerProtocol: ...

    @property
    def time_lane_serializer(self) -> TimeLaneSerializerProtocol: ...

    @property
    def device_manager_extension(self) -> DeviceManagerExtensionProtocol: ...
