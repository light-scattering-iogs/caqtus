from collections.abc import Sequence
from typing import Optional

import numpy as np
from PySide6.QtCharts import (
    QChart,
    QLineSeries,
    QChartView,
    QValueAxis,
)
from PySide6.QtCore import (
    QAbstractTableModel,
    Qt,
    QSortFilterProxyModel,
    QModelIndex,
    QPointF,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QItemEditorFactory,
    QDoubleSpinBox,
    QStyledItemDelegate,
)

from caqtus.gui.common.NodeGraphQt import BaseNode, NodeBaseWidget
from caqtus.gui.condetrol.icons import get_icon
from caqtus.types.parameter import add_unit, magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.types.units.base import convert_to_base_units
from caqtus.utils.itertools import pairwise
from .calibrated_analog_mapping_widget_ui import Ui_CalibratedAnalogMappingWigdet


class CalibratedAnalogMappingNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.mapping"
    NODE_NAME = "Analog mapping"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port = self.add_input("in", multi_input=False)
        self._widget = NodeWidgetWrapper(self.view)
        self.add_custom_widget(self._widget)

    def set_units(
        self, input_units: Optional[str], output_units: Optional[str]
    ) -> None:
        self._widget._widget.set_units(input_units, output_units)

    def set_data_points(self, values: Sequence[tuple[float, float]]) -> None:
        self._widget._widget.set_data_points(values)

    def get_input_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.input_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"

    def get_units(self) -> tuple[Optional[str], Optional[str]]:
        return self._widget._widget.get_units()

    def get_data_points(self) -> list[tuple[float, float]]:
        return self._widget._widget.get_data_points()


class NodeWidgetWrapper(NodeBaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # set the label above the widget.
        self.set_label("Custom Widget")

        # set the custom widget.
        self._widget = CalibratedAnalogMappingWidget()
        self._widget.setStyle(QApplication.style())
        self.set_custom_widget(self._widget)

    def get_value(self):
        return ""

    def set_value(self, text):
        pass


class CalibratedAnalogMappingWidget(QWidget, Ui_CalibratedAnalogMappingWigdet):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

        self._model = Model(self)
        self._sorted_model = QSortFilterProxyModel(self)
        self._sorted_model.setSourceModel(self._model)
        self._sorted_model.sort(0, Qt.SortOrder.AscendingOrder)
        self.tableView.setModel(self._sorted_model)
        self.add_button.setIcon(get_icon("plus"))
        self.remove_button.setIcon(get_icon("minus"))
        self.add_button.clicked.connect(self.on_add_button_clicked)
        self.remove_button.clicked.connect(self.on_remove_button_clicked)

        delegate = QStyledItemDelegate(self)
        delegate.setItemEditorFactory(ItemEditorFactory())
        self.tableView.setItemDelegate(delegate)

        self._chart = QChart()
        self._chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self._series = QLineSeries()
        self._series.setName("Values")

        self._model.dataChanged.connect(self._update_series)
        self._model.rowsInserted.connect(self._update_series)
        self._model.rowsRemoved.connect(self._update_series)
        self._model.modelReset.connect(self._update_series)
        self._chart.addSeries(self._series)

        self.x_axis = QValueAxis()
        self.x_axis.setTitleText("Input")
        self._chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignBottom)
        self._series.attachAxis(self.x_axis)

        self.y_axis = QValueAxis()
        self.y_axis.setTitleText("Output")
        self._chart.addAxis(self.y_axis, Qt.AlignmentFlag.AlignRight)
        self._series.attachAxis(self.y_axis)

        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chartView = QChartView(self._chart, self)
        self._chartView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.inputUnitLineEdit.textChanged.connect(self.set_input_units)
        self.outputUnitLineEdit.textChanged.connect(self.set_output_units)

        self.tabWidget.insertTab(0, self._chartView, "Curve")
        self.tabWidget.setCurrentIndex(0)

    def _update_series(self):
        self._series.clear()
        number_points = self._sorted_model.rowCount()
        if number_points == 0:
            return
        x_points = []
        y_points = []
        for row in range(number_points):
            x_points.append(self._sorted_model.data(self._sorted_model.index(row, 0)))
            y_points.append(self._sorted_model.data(self._sorted_model.index(row, 1)))
        input_units = Unit(u) if (u := self.input_units()) else None
        input_base_points, input_base_units = convert_to_base_units(
            np.array(x_points), input_units
        )

        output_units = Unit(u) if (u := self.output_units()) else None
        y_base_points, y_base_units = convert_to_base_units(
            np.array(y_points), output_units
        )

        input_points = np.concat([np.linspace(a, b, 50) for a, b in pairwise(x_points)])
        interpolation_input_base_points, _ = convert_to_base_units(
            input_points, input_units
        )

        output_points_base = np.interp(
            interpolation_input_base_points, input_base_points, y_base_points
        )
        output_points = magnitude_in_unit(
            add_unit(output_points_base, y_base_units), output_units
        )

        new_points = [QPointF(x, y) for x, y in zip(input_points, output_points)]
        self._series.append(new_points)
        self.auto_scale()

    def set_data_points(self, values: Sequence[tuple[float, float]]) -> None:
        self._model.set_values(values)

    def set_input_units(self, input_units: Optional[str]) -> None:
        if input_units:
            self.inputUnitLineEdit.setText(input_units)
            self.x_axis.setTitleText(f"Input [{input_units}]")
        else:
            # This handles both the case where the input_units is None and the case
            # where the input_units is an empty string.
            self.inputUnitLineEdit.clear()
            self.x_axis.setTitleText("Input")
        self._update_series()

    def set_output_units(self, output_units: Optional[str]) -> None:
        if output_units:
            self.outputUnitLineEdit.setText(output_units)
            self.y_axis.setTitleText(f"Output [{output_units}]")
        else:
            # This handles both the case where the input_units is None and the case
            # where the input_units is an empty string.
            self.outputUnitLineEdit.clear()
            self.y_axis.setTitleText("Output")
        self._update_series()

    def set_units(
        self, input_units: Optional[str], output_units: Optional[str]
    ) -> None:
        self.set_input_units(input_units)
        self.set_output_units(output_units)

    def get_data_points(self) -> list[tuple[float, float]]:
        return self._model.get_values()

    def get_units(self) -> tuple[Optional[str], Optional[str]]:
        return self.input_units(), self.output_units()

    def input_units(self) -> Optional[str]:
        input_units = self.inputUnitLineEdit.text()
        if input_units == "":
            return None
        return input_units

    def output_units(self) -> Optional[str]:
        output_units = self.outputUnitLineEdit.text()
        if output_units == "":
            return None
        return output_units

    def auto_scale(self) -> None:
        self._chart.axisX().setRange(*self._model.x_range())
        self._chart.axisY().setRange(*self._model.y_range())

    def on_add_button_clicked(self):
        self._model.insertRow(
            self._sorted_model.mapToSource(self.tableView.currentIndex()).row() + 1
        )

    def on_remove_button_clicked(self):

        self._model.removeRow(
            self._sorted_model.mapToSource(self.tableView.currentIndex()).row()
        )


class Model(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = []

    def rowCount(self, parent):
        return len(self._values)

    def columnCount(self, parent):
        return 2

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self._values[index.row()][0]
            elif index.column() == 1:
                return self._values[index.row()][1]
        return None

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                self._values[index.row()] = (value, self._values[index.row()][1])
            elif index.column() == 1:
                self._values[index.row()] = (self._values[index.row()][0], value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def set_values(self, values: Sequence[tuple[float, float]]):
        self.beginResetModel()
        self._values = list(values)
        self.endResetModel()

    def get_values(self) -> list[tuple[float, float]]:
        return sorted(self._values)

    def x_range(self):
        return min(x for x, _ in self._values), max(x for x, _ in self._values)

    def y_range(self):
        return min(y for _, y in self._values), max(y for _, y in self._values)

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return "Input"
                elif section == 1:
                    return "Output"
            else:
                return str(section)
        return None

    def insertRow(self, row, parent=QModelIndex()):
        self.beginInsertRows(parent, row, row)
        self._values.insert(row, (0.0, 0.0))
        self.endInsertRows()
        return True

    def removeRow(self, row, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        del self._values[row]
        self.endRemoveRows()
        return True


class ItemEditorFactory(QItemEditorFactory):
    def __init__(self):
        super().__init__()

    def createEditor(self, userType, parent):
        if userType == 6:
            spin_box = QDoubleSpinBox(parent)
            spin_box.setDecimals(3)
            spin_box.setMaximum(1000)
            spin_box.setMinimum(-1000)
            return spin_box
        else:
            return super().createEditor(userType, parent)
