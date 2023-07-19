from typing import Optional

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import QPushButton, QDialog, QFormLayout, QLineEdit, QWidget

from digital_lane.configuration import DigitalLane, Blink
from experiment.configuration import ExperimentConfig
from expression import Expression
from lane.configuration import Lane
from lane.model import LaneModel


class DigitalLaneModel(LaneModel):
    def __init__(
        self, lane: DigitalLane, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(lane, experiment_config, *args, **kwargs)
        self._lane_brush = _get_color(self.lane, self.experiment_config)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        cell_value = self.lane[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(cell_value, Blink):
                return str(cell_value)
        elif role == Qt.ItemDataRole.EditRole:
            return cell_value
        elif role == Qt.ItemDataRole.BackgroundRole:
            if isinstance(cell_value, bool):
                if cell_value:
                    return self._lane_brush
                else:
                    return None
            elif isinstance(cell_value, Blink):
                return self._lane_brush
            else:
                raise NotImplementedError(
                    f"BackgroundRole not implemented for {type(cell_value)}"
                )
        elif role == Qt.ItemDataRole.ForegroundRole:
            return QBrush(QColor.fromRgb(0, 0, 0))

    def setData(
        self, index: QModelIndex, value: bool, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            self.lane[index.row()] = value
            return True
        else:
            return False

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, False)
        self.endInsertRows()
        return True

    def create_editor(self, parent: QWidget, index: QModelIndex) -> QWidget:
        cell_value = self.lane[index.row()]
        if isinstance(cell_value, Blink):
            return BlinkEditor(parent)
        elif isinstance(cell_value, bool):
            return CheckedButton(parent)
        else:
            return NotImplemented

    def set_editor_data(self, editor: QWidget, index: QModelIndex):
        cell_value = self.lane[index.row()]
        if isinstance(cell_value, Blink):
            editor.set_value(cell_value)
        elif isinstance(cell_value, bool):
            editor.setChecked(cell_value)
        else:
            return NotImplemented

    def set_data_from_editor(self, editor: QWidget, index: QModelIndex):
        cell_value = self.lane[index.row()]
        if isinstance(cell_value, Blink):
            self.lane[index.row()] = editor.get_value()
        elif isinstance(cell_value, bool):
            self.lane[index.row()] = editor.isChecked()
        else:
            return NotImplemented


def _get_color(lane: Lane, experiment_config: ExperimentConfig) -> Optional[QBrush]:
    try:
        color = experiment_config.get_color(lane.name)
    except ValueError:
        return QBrush(QColor.fromRgb(0, 0, 0))
    else:
        if color is not None:
            return QBrush(QColor.fromRgb(*color.as_rgb_tuple(alpha=False)))
        else:
            return None


class CheckedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(True)
        self.toggled.connect(self.on_toggled)

    def setChecked(self, a0: bool) -> None:
        super().setChecked(a0)
        self.on_toggled(a0)

    def on_toggled(self, checked: bool):
        if checked:
            self.setText("Enabled")
        else:
            self.setText("Disabled")


class BlinkEditor(QDialog):
    """Widget that allow to edit the blink state of a digital cell."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QFormLayout()

        self.period_widget = QLineEdit()
        self.duty_cycle_widget = QLineEdit()
        self.phase_widget = QLineEdit()
        layout.addRow("Period", self.period_widget)
        layout.addRow("Duty cycle", self.duty_cycle_widget)
        layout.addRow("Phase", self.phase_widget)
        self.setLayout(layout)

        self.setWindowTitle("Configure blink...")

    def set_value(self, blink: Blink):
        self.period_widget.setText(str(blink.period))
        self.duty_cycle_widget.setText(str(blink.duty_cycle))
        self.phase_widget.setText(str(blink.phase))

    def get_value(self) -> Blink:
        return Blink(
            period=Expression(self.period_widget.text()),
            duty_cycle=Expression(self.duty_cycle_widget.text()),
            phase=Expression(self.phase_widget.text()),
        )
