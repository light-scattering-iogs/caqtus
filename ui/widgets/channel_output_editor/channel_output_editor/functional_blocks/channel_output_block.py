from typing import Optional

from PySide6.QtWidgets import (
    QGraphicsItem,
    QWidget,
    QFormLayout,
    QLabel,
    QGraphicsProxyWidget,
)

from .functional_block import FunctionalBlock


class ChannelOutputBlock(FunctionalBlock):
    """A block representing the output of a channel.

    This block has a special meaning in the scene.
    It is the rightmost block in the scene and has no output connection.
    It is the end of the processing pipeline and represents what will be output on the
    channel.
    """

    def __init__(
        self,
        channel_label: str,
        description: str,
        parent: Optional[QGraphicsItem] = None,
    ):
        super().__init__(
            number_input_connections=1, has_output_connection=False, parent=parent
        )
        widget = QWidget()
        layout = QFormLayout(widget)
        widget.setLayout(layout)
        layout.addRow(channel_label, QLabel(description, widget))
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(widget)
        self.set_item(proxy)
