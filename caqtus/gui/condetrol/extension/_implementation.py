from ._protocol import CondetrolExtensionProtocol
from ..device_configuration_editors.extension import CondetrolDeviceExtension
from ..timelanes_editor.extension import CondetrolLaneExtension


class CondetrolExtension(CondetrolExtensionProtocol):
    def __init__(self):
        self.lane_extension = CondetrolLaneExtension()
        self.device_extension = CondetrolDeviceExtension()
