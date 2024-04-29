from collections.abc import Sequence
from typing import Optional

from PySide6.QtCharts import QChart, QLineSeries, QVXYModelMapper, QChartView
from PySide6.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QHBoxLayout, QTableView


class CalibratedAnalogMappingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout()
        self.setLayout(layout)

        self._table = QTableView(self)
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._model = Model(self)
        self._sorted_model = QSortFilterProxyModel(self)
        self._sorted_model.setSourceModel(self._model)
        self._sorted_model.sort(0, Qt.SortOrder.AscendingOrder)
        self._table.setModel(self._sorted_model)
        layout.addWidget(self._table, 0)

        self._chart = QChart()
        self._chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self._series = QLineSeries()
        self._series.pointAdded.connect(self.auto_scale)
        self._series.pointsRemoved.connect(self.auto_scale)
        self._series.pointReplaced.connect(self.auto_scale)
        self._series.setName("Values")
        self._mapper = QVXYModelMapper(self)
        self._mapper.setXColumn(0)
        self._mapper.setYColumn(1)
        self._mapper.setSeries(self._series)
        self._mapper.setModel(self._sorted_model)
        self._chart.addSeries(self._series)
        self._chart.createDefaultAxes()
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chartView = QChartView(self._chart, self)
        self._chartView.setRenderHint(QPainter.Antialiasing)
        self._chart.axisX().setTitleText("Input")
        self._chart.axisY().setTitleText("Output")

        layout.addWidget(self._chartView, 1)

    def set_data_points(self, values: Sequence[tuple[float, float]]) -> None:
        self._model.set_values(values)

    def auto_scale(self) -> None:
        self._chart.axisX().setRange(*self._model.x_range())
        self._chart.axisY().setRange(*self._model.y_range())


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
