from PyQt6.QtCharts import QChartView, QLineSeries, QChart, QValueAxis
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QPainter, QAction
from PyQt6.QtWidgets import QHBoxLayout, QDialog, QTableView, QMenu

from device_config.units_mapping import CalibratedUnitsMapping


class CalibratedMappingEditor(QDialog):
    """Widget to edit the calibrated mapping of a channel

    This widget contains an editable list of measured data points and a view of the
    interpolation between the points.
    """

    def __init__(self, input_label: str, output_label: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setSizeGripEnabled(True)
        self.setWindowTitle("Edit unit mapping...")
        self.resize(400, 300)

        self.layout = QHBoxLayout()

        self.values_view = QTableView()
        self.values_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.values_view.customContextMenuRequested.connect(self.show_context_menu)
        self.model = CalibratedUnitMappingModel(input_label, output_label)
        self.model.mapping_changed.connect(self.set_chart_mapping)
        self.values_view.setModel(self.model)
        self.layout.addWidget(self.values_view, 0)

        self.series = QLineSeries()

        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()

        self.chart = QChart()
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.chart.legend().hide()
        self.chart.setTitle("Unit interpolation")

        self.chart.addSeries(self.series)

        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        self.series.setPointsVisible(True)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.chart_view, 1)

        self.setLayout(self.layout)

    def set_unit_mapping(self, mapping: CalibratedUnitsMapping):
        self.model.set_mapping(mapping)
        self.values_view.resizeColumnsToContents()
        self.set_chart_mapping(mapping)

    def set_chart_mapping(self, mapping: CalibratedUnitsMapping):
        self.series.clear()
        for x, y in zip(mapping.output_values, mapping.input_values):
            self.series.append(x, y)

        self.axis_x.setRange(min(mapping.output_values), max(mapping.output_values))
        self.axis_y.setRange(min(mapping.input_values), max(mapping.input_values))

    def show_context_menu(self, position):
        index = self.values_view.indexAt(position)

        menu = QMenu(self.values_view)

        if index.isValid():
            remove_row = QAction("Remove row")
            remove_row.triggered.connect(
                lambda: self.model.removeRow(index.row(), QModelIndex())
            )
            menu.addAction(remove_row)

        add_row = QAction("Add row")
        add_row.triggered.connect(
            lambda: self.model.insertRow(index.row(), QModelIndex())
        )
        menu.addAction(add_row)

        menu.exec(self.values_view.mapToGlobal(position))


class CalibratedUnitMappingModel(QAbstractTableModel):

    mapping_changed = pyqtSignal(CalibratedUnitsMapping)

    def __init__(self, input_label: str, output_label: str, *args, **kwargs):
        self._mapping: CalibratedUnitsMapping = CalibratedUnitsMapping()
        self._input_label = input_label
        self._output_label = output_label
        super().__init__(*args, **kwargs)

    def set_mapping(self, mapping: CalibratedUnitsMapping):
        self.beginResetModel()
        self._mapping = mapping
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._mapping.input_values)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 2

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self._mapping.output_values[index.row()]
            elif index.column() == 1:
                return self._mapping.input_values[index.row()]

    def setData(self, index: QModelIndex, value: float, role: int = ...) -> bool:
        change = False
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                new_output_values = list(self._mapping.output_values)
                new_output_values[index.row()] = value
                self.beginResetModel()
                self._mapping.output_values = new_output_values
                self.endResetModel()
                change = True
            elif index.column() == 1:
                new_input_values = list(self._mapping.input_values)
                new_input_values[index.row()] = value
                self.beginResetModel()
                self._mapping.input_values = new_input_values
                self.endResetModel()
                change = True
        if change:
            self.mapping_changed.emit(self._mapping)
            self.dataChanged.emit(index, index)
        return change

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return f"{self._output_label} [{self._mapping.get_output_units()}]"
                elif section == 1:
                    return f"{self._input_label} [{self._mapping.get_input_units()}]"
            elif orientation == Qt.Orientation.Vertical:
                return section

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if not (0 <= row < len(self._mapping.input_values)):
            return False
        new_output_values = list(self._mapping.output_values)
        new_output_values.pop(row)
        new_input_values = list(self._mapping.input_values)
        new_input_values.pop(row)
        self.beginRemoveRows(parent, row, row)
        self._mapping.input_values = new_input_values
        self._mapping.output_values = new_output_values
        self.endRemoveRows()
        self.mapping_changed.emit(self._mapping)
        return True

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if row == -1:
            row = len(self._mapping.input_values)
        if not (0 <= row <= len(self._mapping.input_values)):
            return False
        new_output_values = list(self._mapping.output_values)
        new_output_values.insert(row, 0)
        new_input_values = list(self._mapping.input_values)
        new_input_values.insert(row, 0)

        self.beginInsertRows(parent, row, row)
        self._mapping.output_values = new_output_values
        self._mapping.input_values = new_input_values
        self.endInsertRows()
        self.mapping_changed.emit(self._mapping)
        return True
