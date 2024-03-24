from typing import Optional

from PySide6.QtWidgets import (
    QGraphicsItem,
    QWidget,
    QFormLayout,
    QGraphicsProxyWidget,
    QLineEdit,
)

from caqtus.device import DeviceName
from .functional_block import FunctionalBlock


class DeviceTriggerBlock(FunctionalBlock):
    """A block representing a trigger generated for a device.

    This block is a leftmost block in the scene and has no input connections.
    It presents a line edit to input the name of the device for which the trigger is
    generated.
    """

    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=0, has_output_connection=True, parent=parent
        )

        proxy = QGraphicsProxyWidget()
        widget = QWidget()
        layout = QFormLayout()
        widget.setLayout(layout)
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Device name")
        layout.addRow("Trigger", self.line_edit)
        proxy.setWidget(widget)
        self.set_item(proxy)

    def set_device_name(self, device_name: DeviceName) -> None:
        self.line_edit.setText(device_name)

    def get_device_name(self) -> DeviceName:
        return DeviceName(self.line_edit.text())
