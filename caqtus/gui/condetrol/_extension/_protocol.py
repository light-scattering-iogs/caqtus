from typing import Protocol, TypeVar, runtime_checkable

from caqtus.session.shot import TimeLane
from ..device_configuration_editors.extension import CondetrolDeviceExtensionProtocol
from ..timelanes_editor.extension import CondetrolLaneExtensionProtocol

L = TypeVar("L", bound=TimeLane)


@runtime_checkable
class CondetrolExtensionProtocol(Protocol):
    """Defines the operations an extension must implement to be used by Condetrol."""

    device_extension: CondetrolDeviceExtensionProtocol
    lane_extension: CondetrolLaneExtensionProtocol
