from typing import Optional

from caqtus.device import DeviceName
from caqtus.gui.common.NodeGraphQt import BaseNode


class DeviceTriggerNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.source"
    NODE_NAME = "Device trigger"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.default_port = self.add_input("absent?", multi_input=False)
        self.add_text_input(
            "Device",
            text="...",
            placeholder_text="device name",
            tooltip="The name of the device for which to generate a trigger",
        )

    def set_device_name(self, device_name: DeviceName) -> None:
        self.set_property("Device", device_name)

    def get_device_name(self) -> DeviceName:
        return DeviceName(str(self.get_property("Device")))

    def get_default_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.default_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"
