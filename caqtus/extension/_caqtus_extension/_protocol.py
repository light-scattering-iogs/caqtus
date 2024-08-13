from typing import Protocol

from caqtus.device.configuration.serializer import DeviceConfigJSONSerializerProtocol
from caqtus.experiment_control.device_manager_extension import (
    DeviceManagerExtensionProtocol,
)
from caqtus.gui.condetrol._extension import CondetrolExtensionProtocol
from caqtus.types.timelane.serializer import TimeLaneSerializerProtocol


class CaqtusExtensionProtocol(Protocol):
    condetrol_extension: CondetrolExtensionProtocol
    device_configurations_serializer: DeviceConfigJSONSerializerProtocol
    time_lane_serializer: TimeLaneSerializerProtocol
    device_manager_extension: DeviceManagerExtensionProtocol
