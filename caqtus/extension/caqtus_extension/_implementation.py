import attrs

from caqtus.gui.condetrol.extension import CondetrolExtension
from ._protocol import CaqtusExtensionProtocol
from ..device_extension import DeviceExtension


@attrs.frozen
class CaqtusExtension(CaqtusExtensionProtocol):
    condetrol_extension: CondetrolExtension = attrs.field(factory=CondetrolExtension)

    def register_device_extension(self, device_extension: DeviceExtension) -> None:
        self.condetrol_extension.device_extension.register_device_configuration_editor(
            device_extension.configuration_type, device_extension.editor_type
        )
        self.condetrol_extension.device_extension.register_configuration_factory(
            device_extension.label, device_extension.configuration_factory
        )
