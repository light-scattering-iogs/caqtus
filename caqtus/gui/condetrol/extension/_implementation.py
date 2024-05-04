import attrs

from ._protocol import CondetrolExtensionProtocol
from ..device_configuration_editors.extension import CondetrolDeviceExtension
from ..timelanes_editor.extension import CondetrolLaneExtension


@attrs.define
class CondetrolExtension(CondetrolExtensionProtocol):
    lane_extension: CondetrolLaneExtension = attrs.field(factory=CondetrolLaneExtension)
    device_extension: CondetrolDeviceExtension = attrs.field(
        factory=CondetrolDeviceExtension
    )
