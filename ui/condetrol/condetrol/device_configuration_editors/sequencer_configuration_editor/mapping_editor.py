from PySide6 import QtGui
from PySide6.QtCharts import QChartView, QLineSeries, QChart, QValueAxis
from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    Signal,
    QSortFilterProxyModel,
    QSettings,
)
from PySide6.QtGui import QPainter, QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QDialog,
    QTableView,
    QMenu,
    QItemEditorFactory,
    QDoubleSpinBox,
    QWidget,
    QStyledItemDelegate,
    QSplitter,
    QHeaderView,
    QInputDialog,
    QLineEdit,
)

from core.device.sequencer.configuration import CalibratedAnalogMapping


class CalibratedMappingEditor(QDialog):
    """Widget to edit the calibrated mapping of a channel

    This widget contains an editable list of measured data points and a view of the
    interpolation between the points.
    """

    def __init__(self, input_label: str, output_label: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._input_label = input_label
        self._output_label = output_label

        self.setSizeGripEnabled(True)
        self.setWindowTitle("Edit unit mapping...")
        self.resize(400, 300)

        self._layout = QHBoxLayout()
        self.splitter = QSplitter(orientation=Qt.Orientation.Horizontal)
        self._layout.addWidget(self.splitter)

        self.values_view = QTableView()
        self.values_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.values_view.customContextMenuRequested.connect(self.show_context_menu)
        delegate = QStyledItemDelegate(self)
        delegate.setItemEditorFactory(ItemEditorFactory())
        self.values_view.setItemDelegate(delegate)

        self.values_view.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.values_view.horizontalHeader().customContextMenuRequested.connect(
            self.show_header_context_menu
        )

        self.model = CalibratedUnitMappingModel(input_label, output_label)
        self.model.mapping_changed.connect(self.set_chart_mapping)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.values_view.setModel(self.proxy_model)
        self.values_view.setSortingEnabled(True)
        self.values_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.values_view.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.splitter.addWidget(self.values_view)

        self.series = QLineSeries()

        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()

        self.chart = QChart()
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.chart.legend().hide()

        self.chart.addSeries(self.series)

        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        self.series.setPointsVisible(True)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.splitter.addWidget(self.chart_view)

        ui_settings = QSettings("Caqtus", "ExperimentControl")
        self.splitter.restoreState(
            ui_settings.value(f"{__name__}/splitter_state", self.splitter.saveState())
        )

        self.setLayout(self._layout)

    def show_header_context_menu(self, position):
        index = self.values_view.horizontalHeader().logicalIndexAt(position)

        menu = QMenu(self.values_view)

        if index == 1:
            change_units = QAction("Change units")
            change_units.triggered.connect(self.change_units)
            menu.addAction(change_units)
            menu.exec(self.values_view.mapToGlobal(position))

    def change_units(self):
        text, ok = QInputDialog().getText(
            self,
            f"Change units for {self._input_label}",
            "New units:",
            QLineEdit.EchoMode.Normal,
            self.model.mapping.get_input_units(),
        )
        if ok:
            self.model.set_input_units(text)
            self.set_chart_mapping(self.model.mapping)
            self.values_view.update()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        ui_settings = QSettings("Caqtus", "ExperimentControl")
        ui_settings.setValue(f"{__name__}/splitter_state", self.splitter.saveState())

    def set_unit_mapping(self, mapping: CalibratedAnalogMapping):
        self.model.set_mapping(mapping)
        self.values_view.resizeColumnsToContents()
        self.set_chart_mapping(mapping)

    def get_mapping(self) -> CalibratedAnalogMapping:
        return self.model.mapping

    def set_chart_mapping(self, mapping: CalibratedAnalogMapping):
        self.series.clear()
        for x, y in zip(mapping.output_values, mapping.input_values):
            self.series.append(x, y)

        self.axis_x.setRange(min(mapping.output_values), max(mapping.output_values))
        self.axis_y.setRange(min(mapping.input_values), max(mapping.input_values))
        self.axis_x.setTitleText(f"{self._output_label} [{mapping.get_output_units()}]")
        self.axis_y.setTitleText(f"{self._input_label} [{mapping.get_input_units()}]")

    def show_context_menu(self, position):
        index = self.values_view.indexAt(position)

        menu = QMenu(self.values_view)

        if index.isValid():
            remove_row = QAction("Remove row")
            remove_row.triggered.connect(
                lambda: index.model().removeRow(index.row(), QModelIndex())
            )
            menu.addAction(remove_row)
        else:
            index = self.values_view.model().index(-1, 0)

        add_row = QAction("Add row")
        add_row.triggered.connect(
            lambda: index.model().insertRow(index.row(), QModelIndex())
        )
        menu.addAction(add_row)

        menu.exec(self.values_view.mapToGlobal(position))

    @staticmethod
    def remove_row(index: QModelIndex):
        index.model().removeRow(index.row(), QModelIndex())


class CalibratedUnitMappingModel(QAbstractTableModel):
    mapping_changed = Signal(CalibratedAnalogMapping)

    def __init__(self, input_label: str, output_label: str, *args, **kwargs):
        self._mapping: CalibratedAnalogMapping = CalibratedAnalogMapping()
        self._input_label = input_label
        self._output_label = output_label
        super().__init__(*args, **kwargs)

    def set_mapping(self, mapping: CalibratedAnalogMapping):
        self.beginResetModel()
        self._mapping = mapping
        self.endResetModel()

    @property
    def mapping(self) -> CalibratedAnalogMapping:
        return self._mapping

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._mapping.input_values)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self._mapping.output_values[index.row()]
            elif index.column() == 1:
                return self._mapping.input_values[index.row()]

    def setData(
        self, index: QModelIndex, value: float, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        change = False
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                self.beginResetModel()
                self._mapping.set_output(index.row(), value)
                self.endResetModel()
                change = True
            elif index.column() == 1:
                self.beginResetModel()
                self._mapping.set_input(index.row(), value)
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

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return f"{self._output_label} [{self._mapping.get_output_units()}]"
                elif section == 1:
                    return f"{self._input_label} [{self._mapping.get_input_units()}]"
            elif orientation == Qt.Orientation.Vertical:
                return section

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row < len(self._mapping.input_values)):
            return False
        self.beginRemoveRows(parent, row, row)
        self._mapping.pop(row)
        self.endRemoveRows()
        self.mapping_changed.emit(self._mapping)
        return True

    def removeRows(
        self, row: int, count: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        for _ in range(count):
            self.removeRow(row, parent)
        return True

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        if row == -1:
            row = len(self._mapping.input_values)
        if not (0 <= row <= len(self._mapping.input_values)):
            return False
        self.beginInsertRows(parent, row, row)
        self._mapping.insert(row, 0, 0)
        self.endInsertRows()
        self.mapping_changed.emit(self._mapping)
        return True

    def insertRows(
        self, row: int, count: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        for _ in range(count):
            self.insertRow(row, parent)
        return True

    def set_input_units(self, units: str):
        self._mapping.input_units = units
        self.mapping_changed.emit(self._mapping)
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 1, 1)


class ItemEditorFactory(QItemEditorFactory):
    def createEditor(self, user_type: int, parent: QWidget) -> QWidget:
        QVARIANT_DOUBLE = 6  # can't find the ref in the Qt docs
        if user_type == QVARIANT_DOUBLE:
            double_spin_box = QDoubleSpinBox(parent)
            double_spin_box.setDecimals(3)
            double_spin_box.setMaximum(1000)
            double_spin_box.setMinimum(-1000)
            return double_spin_box
        else:
            return super().createEditor(user_type, parent)
