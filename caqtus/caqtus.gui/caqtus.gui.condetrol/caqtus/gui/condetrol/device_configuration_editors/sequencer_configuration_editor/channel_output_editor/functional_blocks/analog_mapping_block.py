from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGraphicsProxyWidget,
    QGraphicsItem,
    QWidget,
    QVBoxLayout,
    QLabel, QPushButton, QDialog,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .functional_block import FunctionalBlock


class CalibratedAnalogMappingItem(QGraphicsProxyWidget):
    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setWidget(CalibratedAnalogMappingWidget())


class AnalogMappingBlock(FunctionalBlock):
    """Represents a function mapping an input quantity to an output quantity."""

    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=1, has_output_connection=True, parent=parent
        )
        proxy = QGraphicsProxyWidget()
        widget = QWidget()
        widget.setLayout(layout := QVBoxLayout())
        layout.addWidget(QLabel("Analog Mapping"))
        self.edit_button = QPushButton("Edit")
        layout.addWidget(self.edit_button)
        self.mapping_widget = CalibratedAnalogMappingWidget()
        layout.addWidget(self.mapping_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        proxy.setWidget(widget)
        self.set_item(proxy)

    def set_data_points(self, x: list[float], y: list[float]) -> None:
        self.mapping_widget.set_data_points(x, y)

    def get_data_points(self) -> tuple[list[float], list[float]]:
        return self.mapping_widget.get_data_points()

    def set_input_units(self, units: Optional[str]) -> None:
        self.mapping_widget.set_input_units(units)

    def get_input_units(self) -> Optional[str]:
        return self.mapping_widget.get_input_units()

    def set_output_units(self, units: Optional[str]) -> None:
        self.mapping_widget.set_output_units(units)

    def get_output_units(self) -> Optional[str]:
        return self.mapping_widget.get_output_units()


class CalibratedAnalogMappingWidget(FigureCanvasQTAgg):
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(4, 3))
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.x: list[float] = []
        self.y: list[float] = []
        self.input_units: Optional[str] = None
        self.output_units: Optional[str] = None
        (self.line,) = self.axes.plot([], [], "-o")
        self.axes.set_xlabel(r"Input $x(t)$")
        self.axes.set_ylabel(r"Output $y(t)$")
        self.axes.yaxis.tick_right()
        self.axes.yaxis.set_label_position("right")
        self.figure.tight_layout()
        self.axes.grid(True)

    def set_data_points(self, x: list[float], y: list[float]) -> None:
        self.x, self.y = x, y
        self.line.set_data(x, y)
        self.axes.relim()
        self.axes.autoscale_view()
        self.figure.tight_layout()
        self.draw()

    def get_data_points(self) -> tuple[list[float], list[float]]:
        return self.x, self.y

    def set_input_units(self, units: Optional[str]) -> None:
        self.input_units = units
        self.axes.set_xlabel(f"Input $x(t)$ [{units}]")
        self.figure.tight_layout()
        self.draw()

    def get_input_units(self) -> Optional[str]:
        return self.input_units

    def set_output_units(self, units: Optional[str]) -> None:
        self.output_units = units
        self.axes.set_ylabel(f"Output $y(t)$ [{units}]")
        self.figure.tight_layout()
        self.draw()

    def get_output_units(self) -> Optional[str]:
        return self.output_units

class CalibratedMappingValuesDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setLayout(layout := QVBoxLayout())
        self.setModal(True)
        self.setWindowTitle("Calibrated Mapping Values")
        self.x = QLabel()
        self.y = QLabel()
        layout.addWidget(self.x)
        layout.addWidget(self.y)
