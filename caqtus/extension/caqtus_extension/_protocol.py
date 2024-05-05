from typing import Protocol

from caqtus.device.configuration.serializer import DeviceConfigJSONSerializerProtocol
from caqtus.gui.condetrol.extension import CondetrolExtensionProtocol


class CaqtusExtensionProtocol(Protocol):
    condetrol_extension: CondetrolExtensionProtocol
    device_configurations_serializer: DeviceConfigJSONSerializerProtocol
