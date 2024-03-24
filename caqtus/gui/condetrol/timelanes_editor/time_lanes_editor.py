import functools
import itertools
from collections.abc import Mapping
from typing import Optional, Protocol

from PySide6.QtCore import Signal, Qt, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QTableView,
    QMenu,
    QStyledItemDelegate,
    QWidget,
    QVBoxLayout,
    QToolBar,
    QDialog,
    QMessageBox,
)

from caqtus.device import DeviceConfigurationAttrs, DeviceName
from caqtus.gui.condetrol.icons import get_icon
from caqtus.session import ParameterNamespace
from caqtus.session.shot import TimeLanes, TimeLane, DigitalTimeLane
from .add_lane_dialog import AddLaneDialog
from .digital_lane_delegate import DigitalTimeLaneDelegate
from .model import TimeLanesModel, TimeLaneModel
from ...common.qtutil import block_signals


class LaneModelFactory(Protocol):
    """A factory for lane models."""

    def __call__(self, lane: TimeLane) -> type[TimeLaneModel]: ...


class LaneDelegateFactory(Protocol):
    """A factory for lane delegates."""

    def __call__(
        self,
        lane_name: str,
        lane: TimeLane,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
        sequence_parameters: ParameterNamespace,
        parent: QWidget,
    ) -> Optional[QStyledItemDelegate]: ...


def default_lane_delegate_factory(
    lane_name: str,
    lane: TimeLane,
    device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    sequence_parameters: ParameterNamespace,
    parent: QWidget,
) -> Optional[QStyledItemDelegate]:
    if isinstance(lane, DigitalTimeLane):
        return DigitalTimeLaneDelegate(parent)
    else:
        return None


class LaneFactory(Protocol):
    def __call__(self, number_steps: int) -> TimeLane: ...


class TimeLanesEditor(QWidget):
    """A widget for editing the time lanes of a sequence.

    Signals:
        time_lanes_edited: Emitted when the user edits the time lanes.
    """

    time_lanes_edited = Signal(TimeLanes)

    def __init__(
        self,
        lane_factories: Mapping[str, LaneFactory],
        lane_model_factory: LaneModelFactory,
        lane_delegate_factory: LaneDelegateFactory,
        device_configurations: dict[DeviceName, DeviceConfigurationAttrs],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.view = TimeLanesView(
            lane_model_factory=lane_model_factory,
            lane_delegate_factory=lane_delegate_factory,
            device_configurations=device_configurations,
            parent=self,
        )
        self.view.time_lanes_changed.connect(self.time_lanes_edited)
        self.toolbar = QToolBar(self)
        self.add_lane_action = self.toolbar.addAction(
            get_icon("add-time-lane", self.palette().buttonText().color()), "Add lane"
        )
        self.add_lane_action.triggered.connect(self._on_add_lane_triggered)
        self.simplify_action = self.toolbar.addAction(
            get_icon("simplify-timelanes", self.palette().buttonText().color()),
            "Simplify",
        )
        self.simplify_action.triggered.connect(self._simplify_timelanes)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self._add_lane_dialog = AddLaneDialog(self)
        self._add_lane_dialog.set_lane_types(lane_factories)
        self._lane_factories = lane_factories

    def set_read_only(self, read_only: bool) -> None:
        """Set the editor to read-only mode.

        In read-only mode, the user cannot edit the time lanes.
        """

        self.view.set_read_only(read_only)
        self.toolbar.setEnabled(not read_only)

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        """Set the time lanes to be edited.

        The signal time_lanes_edited is not emitted when this method is called.
        """

        with block_signals(self):
            self.view.set_time_lanes(time_lanes)

    def _simplify_timelanes(self):
        self.view.simplify_timelanes()

    def _on_add_lane_triggered(self) -> None:
        if self._add_lane_dialog.exec() == QDialog.DialogCode.Accepted:
            lane_name = self._add_lane_dialog.get_lane_name()
            lane_type = self._add_lane_dialog.get_lane_type()
            if not lane_name:
                return
            if lane_name in self.view.get_time_lanes().lanes:
                QMessageBox.warning(
                    self,
                    "Lane already exists",
                    f"Can't add the lane <i>{lane_name}</i> because there is already "
                    "a lane with this name.",
                )
            else:
                lane_factory = self._lane_factories[lane_type]
                lane = lane_factory(self.view.model().columnCount())
                self.view.add_lane(lane_name, lane)


class TimeLanesView(QTableView):
    time_lanes_changed = Signal(TimeLanes)

    def __init__(
        self,
        lane_model_factory: LaneModelFactory,
        lane_delegate_factory: LaneDelegateFactory,
        device_configurations: dict[DeviceName, DeviceConfigurationAttrs],
        parent: Optional[QWidget] = None,
    ):
        """A widget for editing time lanes.

        Parameters:
            lane_delegate_factory: A factory for lane delegates.
            This is a callable that allows to customize how a lane should be displayed
            and edited.
            When a lane is displayed, the factory is called with the lane, the default
            device configurations and the default constant tables.
            If the factory returns a QStyledItemDelegate, it is set for the view row
            corresponding to the lane.
            It is up to the factory to create a delegate per lane or to reuse the same
            delegate for multiple lanes.
            parent: The parent widget.
        """

        super().__init__(parent)
        self._model = TimeLanesModel(lane_model_factory, self)
        self._device_configurations: dict[DeviceName, DeviceConfigurationAttrs] = (
            device_configurations
        )
        self._sequence_parameters = ParameterNamespace.empty()
        self.lane_delegate_factory = functools.partial(
            lane_delegate_factory,
            device_configurations=self._device_configurations,
            sequence_parameters=self._sequence_parameters,
            parent=self,
        )
        self.setModel(self._model)

        self.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.verticalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setup_connections()

        # self.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QTableView.SelectionMode.ContiguousSelection)

    def setup_connections(self):
        self.horizontalHeader().customContextMenuRequested.connect(
            self.show_steps_context_menu
        )
        self.verticalHeader().customContextMenuRequested.connect(
            self.show_lanes_context_menu
        )
        self.customContextMenuRequested.connect(self.show_cell_context_menu)

        self._model.dataChanged.connect(self.on_data_changed)
        self._model.rowsInserted.connect(self.on_time_lanes_changed)
        self._model.rowsInserted.connect(self.update_delegates)
        self._model.rowsRemoved.connect(self.on_time_lanes_changed)
        self._model.columnsInserted.connect(self.on_time_lanes_changed)
        self._model.columnsRemoved.connect(self.on_time_lanes_changed)

        self._model.modelReset.connect(self.update_spans)
        self._model.modelReset.connect(self.on_time_lanes_changed)
        self._model.modelReset.connect(self.update_delegates)

    def on_time_lanes_changed(self):
        self.time_lanes_changed.emit(self.get_time_lanes())

    def on_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        self.on_time_lanes_changed()

        for row in range(top_left.row(), bottom_right.row() + 1):
            for column in range(top_left.column(), bottom_right.column() + 1):
                index = self._model.index(row, column, QModelIndex())
                span = self._model.span(index)
                if span.width() >= 1 or span.height() >= 1:
                    self.setSpan(row, column, span.height(), span.width())

    def get_time_lanes(self) -> TimeLanes:
        return self._model.get_timelanes()

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        self._model.set_timelanes(time_lanes)

    def update_spans(self):
        self.clearSpans()
        for row in range(self._model.rowCount()):
            for column in range(self._model.columnCount()):
                index = self._model.index(row, column, QModelIndex())
                span = self._model.span(index)
                if span.width() >= 1 or span.height() >= 1:
                    self.setSpan(row, column, span.height(), span.width())

    def update_delegates(self):
        for row in range(self._model.rowCount()):
            previous_delegate = self.itemDelegateForRow(row)
            if previous_delegate:
                previous_delegate.deleteLater()
            self.setItemDelegateForRow(row, None)
        for row in range(2, self._model.rowCount()):
            lane = self._model.get_lane(row - 2)
            name = self._model.get_lane_name(row - 2)
            delegate = self.lane_delegate_factory(name, lane)
            self.setItemDelegateForRow(row, delegate)
            if delegate:
                delegate.setParent(self)

    def set_read_only(self, read_only: bool) -> None:
        self._model.set_read_only(read_only)

    def show_steps_context_menu(self, pos):
        menu = QMenu(self.horizontalHeader())

        index = self.horizontalHeader().logicalIndexAt(pos.x())
        if index == -1:
            add_step_action = QAction("Add step")
            menu.addAction(add_step_action)
            add_step_action.triggered.connect(
                lambda: self._model.insertColumn(
                    self._model.columnCount(), QModelIndex()
                )
            )
        elif 0 <= index < self.model().columnCount():
            add_step_before_action = QAction("Insert step before")
            menu.addAction(add_step_before_action)
            add_step_before_action.triggered.connect(
                lambda: self._model.insertColumn(index, QModelIndex())
            )

            add_step_after_action = QAction("Insert step after")
            menu.addAction(add_step_after_action)
            add_step_after_action.triggered.connect(
                lambda: self._model.insertColumn(index + 1, QModelIndex())
            )
            if self.model().columnCount() > 1:
                remove_step_action = QAction("Remove")
                menu.addAction(remove_step_action)
                remove_step_action.triggered.connect(
                    lambda: self._model.removeColumn(index, QModelIndex())
                )
        menu.exec(self.horizontalHeader().mapToGlobal(pos))
        menu.deleteLater()

    def show_lanes_context_menu(self, pos):
        menu = QMenu(self.verticalHeader())

        index = self.verticalHeader().logicalIndexAt(pos.y())
        if 2 <= index < self.model().rowCount():
            remove_lane_action = QAction("Remove")
            menu.addAction(remove_lane_action)
            remove_lane_action.triggered.connect(
                lambda: self._model.removeRow(index, QModelIndex())
            )
            for action in self._model.get_lane_header_context_actions(index - 2):
                if isinstance(action, QAction):
                    menu.addAction(action)
                elif isinstance(action, QMenu):
                    menu.addMenu(action)
        else:
            return
        menu.exec(self.verticalHeader().mapToGlobal(pos))
        menu.deleteLater()

    def show_cell_context_menu(self, pos):
        index = self.indexAt(pos)
        cell_actions = self._model.get_cell_context_actions(index)
        selection = self.selectionModel().selection()

        menu = QMenu(self)
        if selection.contains(index):
            merge_action = menu.addAction(f"Expand step {index.column()}")
            merge_action.triggered.connect(
                lambda: self.expand_step(index.column(), selection)
            )

        for action in cell_actions:
            if isinstance(action, QAction):
                menu.addAction(action)
            elif isinstance(action, QMenu):
                menu.addMenu(action)
        menu.exec(self.viewport().mapToGlobal(pos))
        menu.deleteLater()
        # TODO: Deal with model change in the context menu better
        self._model.modelReset.emit()

    def expand_step(self, step: int, selection):
        indices: set[tuple[int, int]] = set()
        for selection_range in selection:
            top_left = selection_range.topLeft()
            bottom_right = selection_range.bottomRight()
            indices.update(
                itertools.product(
                    range(top_left.row(), bottom_right.row() + 1),
                    range(top_left.column(), bottom_right.column() + 1),
                )
            )

        for row, group in itertools.groupby(sorted(indices), key=lambda x: x[0]):
            group = list(group)
            start = group[0][1]
            stop = group[-1][1]
            self._model.expand_step(step, row - 2, start, stop)

    def simplify_timelanes(self):
        self._model.simplify()

    def add_lane(self, lane_name: str, lane: TimeLane):
        self._model.insert_time_lane(lane_name, lane)
