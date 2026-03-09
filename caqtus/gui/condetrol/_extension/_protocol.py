from typing import Protocol, runtime_checkable

from ..device_configuration_editors._extension import CondetrolDeviceExtensionProtocol
from ..timelanes_editor.extension import CondetrolLaneExtensionProtocol


@runtime_checkable
class CondetrolExtensionProtocol(Protocol):
    """Defines the operations an extension must implement to be used by Condetrol."""

    @property
    def device_extension(self) -> CondetrolDeviceExtensionProtocol: ...

    @property
    def lane_extension(self) -> CondetrolLaneExtensionProtocol: ...
