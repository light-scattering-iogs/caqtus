import attrs

from ._protocol import CondetrolExtensionProtocol
from ..device_configuration_editors._extension import CondetrolDeviceExtension
from ..timelanes_editor.extension import CondetrolLaneExtension


@attrs.define
class CondetrolExtension(CondetrolExtensionProtocol):
    _lane_extension: CondetrolLaneExtension = attrs.field(
        factory=CondetrolLaneExtension
    )
    _device_extension: CondetrolDeviceExtension = attrs.field(
        factory=CondetrolDeviceExtension
    )

    @property
    def lane_extension(self) -> CondetrolLaneExtension:
        return self._lane_extension

    @property
    def device_extension(self) -> CondetrolDeviceExtension:
        return self._device_extension
