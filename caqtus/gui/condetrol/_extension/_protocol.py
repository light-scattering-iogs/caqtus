from typing import Protocol, runtime_checkable

from ..device_configuration_editors.extension import CondetrolDeviceExtensionProtocol
from ..timelanes_editor.extension import CondetrolLaneExtensionProtocol


@runtime_checkable
class CondetrolExtensionProtocol(Protocol):
    """Defines the operations an extension must implement to be used by Condetrol."""

    device_extension: CondetrolDeviceExtensionProtocol
    lane_extension: CondetrolLaneExtensionProtocol
