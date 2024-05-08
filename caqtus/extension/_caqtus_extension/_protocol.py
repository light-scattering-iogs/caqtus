from typing import Protocol

from caqtus.device.configuration.serializer import DeviceConfigJSONSerializerProtocol
from caqtus.gui.condetrol.extension import CondetrolExtensionProtocol
from caqtus.types.timelane import TimeLaneSerializerProtocol


class CaqtusExtensionProtocol(Protocol):
    condetrol_extension: CondetrolExtensionProtocol
    device_configurations_serializer: DeviceConfigJSONSerializerProtocol
    time_lane_serializer: TimeLaneSerializerProtocol
