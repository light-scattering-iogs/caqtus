from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGraphicsProxyWidget,
    QGraphicsItem,
    QWidget,
    QFormLayout,
    QVBoxLayout,
    QLabel,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from .item_container import FunctionalBlock


class CalibratedAnalogMappingItem(QGraphicsProxyWidget):
    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setWidget(CalibratedAnalogMappingWidget())


class AnalogMappingBlock(FunctionalBlock):
    """The output"""

    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=1, has_output_connection=True, parent=parent
        )
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Analog Mapping"))
        layout.addWidget(CalibratedAnalogMappingWidget())
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setLayout(layout)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(widget)
        self.set_item(proxy)


class CalibratedAnalogMappingWidget(FigureCanvasQTAgg):
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(3, 2))
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.axes.plot([-20, +20], [-6, +6], "-o")
        self.axes.set_xlabel("Input [MHz]")
        self.axes.set_ylabel("Output [V]")
        self.axes.yaxis.tick_right()
        self.axes.yaxis.set_label_position("right")
        self.figure.tight_layout()
        self.axes.grid(True)
