import logging
from functools import partial

from PyQt6.QtCore import Qt, QModelIndex, QAbstractItemModel
from PyQt6.QtGui import QPainter, QBrush, QColor, QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import (
    QWidget,
    QTableView,
    QVBoxLayout,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QMenu,
)

from experiment_config import ExperimentConfig
from experiment_session import ExperimentSessionMaker
from sequence.configuration import DigitalLane, AnalogLane, CameraLane, TakePicture
from sequence.runtime import Sequence
from sequence.runtime.state import State
from .swim_lane_model import SwimLaneModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class LaneCellDelegate(QStyledItemDelegate):
    def __init__(self, experiment_config: ExperimentConfig):
        super().__init__()
        self.experiment_config = experiment_config

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        # noinspection PyTypeChecker
        model: SwimLaneModel = index.model()
        lane = model.get_lane(index)
        if isinstance(lane, DigitalLane):
            if index.data(Qt.ItemDataRole.DisplayRole):
                try:
                    color = self.experiment_config.get_color(lane.name)
                except ValueError:
                    brush = QBrush(QColor.fromRgb(0, 0, 0))
                else:
                    if color is not None:
                        brush = QBrush(QColor.fromRgb(*color.as_rgb_tuple(alpha=False)))
                    else:
                        brush = QBrush(option.palette.highlightedText().color())
                painter.fillRect(option.rect, brush)
            if option.state & QStyle.StateFlag.State_Selected:
                c = option.palette.highlight().color()
                c.setAlphaF(0.8)
                brush = QBrush(c)
                painter.fillRect(option.rect, brush)
        else:
            super().paint(painter, option, index)


class ShotWidget(QWidget):
    """A widget that shows the timeline of a shot

    Columns represent the different steps of the shot. Rows represent the different
    lanes (i.e. action channels).

    """

    def __init__(
        self,
        sequence: Sequence,
        experiment_config: ExperimentConfig,
        session_maker: ExperimentSessionMaker,
        *args
    ):
        super().__init__(*args)
        self._sequence = sequence

        self.experiment_config = experiment_config

        self.model = SwimLaneModel(
            self._sequence, "shot", self.experiment_config, session_maker
        )

        self.layout = QVBoxLayout()
        self.layout.addWidget(SwimLaneWidget(self.model, sequence, session_maker))
        self.setLayout(self.layout)

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)

    def undo(self):
        self.model.undo()

    def redo(self):
        self.model.redo()

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.model.update_experiment_config(new_config)


class SpanTableView(QTableView):
    def __init__(self):
        super().__init__()

    def setModel(self, model: QAbstractItemModel) -> None:
        super().setModel(model)
        # noinspection PyUnresolvedReferences
        self.model().layoutChanged.connect(self.update_span)
        # noinspection PyUnresolvedReferences
        self.model().layoutChanged.emit()

    def update_span(self):
        self.clearSpans()
        for row in range(self.model().rowCount()):
            for column in range(self.model().columnCount()):
                index = self.model().index(row, column, QModelIndex())
                span = self.model().span(index)
                self.setSpan(row, column, span.height(), span.width())


class SwimLaneWidget(QWidget):
    def __init__(
        self,
        model: SwimLaneModel,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        *args
    ):
        super().__init__(*args)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        self.setLayout(QVBoxLayout())

        self._model = model
        self._sequence = sequence
        self._session = session_maker()

        self.steps_view = QTableView()
        self.steps_view.setModel(self._model)
        self.hide_time_table_lanes()
        self._model.rowsInserted.connect(self.hide_time_table_lanes)

        self.steps_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.steps_view.setAlternatingRowColors(True)
        policy = self.steps_view.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
        self.steps_view.setSizePolicy(policy)
        self.update_section_height()
        self.steps_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.steps_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.lanes_view = SpanTableView()
        self.lanes_view.setItemDelegate(LaneCellDelegate(model.experiment_config))
        self.lanes_view.setModel(self._model)
        self.lanes_view.horizontalHeader().hide()
        self.lanes_view.setRowHidden(0, True)
        self.lanes_view.setRowHidden(1, True)

        policy = self.lanes_view.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.MinimumExpanding)
        self.lanes_view.setSizePolicy(policy)
        self.lanes_view.setMinimumHeight(0)

        splitter.addWidget(self.steps_view)
        splitter.addWidget(self.lanes_view)

        self.layout().addWidget(splitter)

        self.update_vertical_header_width()
        # noinspection PyUnresolvedReferences
        self.steps_view.horizontalHeader().sectionResized.connect(
            self.update_section_width
        )
        # noinspection PyUnresolvedReferences
        self.steps_view.verticalHeader().sectionResized.connect(
            self.update_section_height
        )
        # noinspection PyUnresolvedReferences
        self.lanes_view.horizontalScrollBar().valueChanged.connect(
            self.steps_view.horizontalScrollBar().setValue
        )

        self.steps_view.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        # noinspection PyUnresolvedReferences
        self.steps_view.horizontalHeader().customContextMenuRequested.connect(
            self.show_steps_context_menu
        )

        self.lanes_view.verticalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        # noinspection PyUnresolvedReferences
        self.lanes_view.verticalHeader().customContextMenuRequested.connect(
            self.show_lanes_context_menu
        )

        self.lanes_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # noinspection PyUnresolvedReferences
        self.lanes_view.customContextMenuRequested.connect(
            self.show_lane_cells_context_menu
        )

    def get_sequence_state(self, session) -> State:
        return self._sequence.get_state(session)

    def hide_time_table_lanes(self, *_):
        for i in range(2, self._model.rowCount()):
            self.steps_view.setRowHidden(i, True)

    def update_vertical_header_width(self):
        new_width = max(
            self.lanes_view.verticalHeader().width(),
            self.steps_view.verticalHeader().width(),
        )
        self.lanes_view.verticalHeader().setFixedWidth(new_width)
        self.steps_view.verticalHeader().setFixedWidth(new_width)

    def update_section_width(self, logical_index: int, old_size: int, new_size: int):
        self.lanes_view.setColumnWidth(logical_index, new_size)

    def update_section_height(self, *_):
        height = (
            self.steps_view.horizontalHeader().height()
            + self.steps_view.rowHeight(0)
            + self.steps_view.rowHeight(1)
            + 5
        )
        self.steps_view.setFixedHeight(height)

    def show_lanes_context_menu(self, position):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
        menu = QMenu(self.lanes_view.verticalHeader())
        index = self.lanes_view.verticalHeader().logicalIndexAt(position)

        if index == -1:
            add_lane_menu = QMenu()
            add_lane_menu.setTitle("Add lane...")
            menu.addMenu(add_lane_menu)
            add_digital_lane_menu = QMenu("digital")
            digital_actions = self.create_digital_add_lane_actions()
            for digital_action in digital_actions:
                add_digital_lane_menu.addAction(digital_action)
            add_lane_menu.addMenu(add_digital_lane_menu)

            add_analog_lane_menu = QMenu("analog")
            analog_actions = self.create_analog_add_lane_actions()
            for analog_action in analog_actions:
                add_analog_lane_menu.addAction(analog_action)
            add_lane_menu.addMenu(add_analog_lane_menu)

            camera_actions = self.create_camera_add_lane_actions()
            if len(camera_actions) > 0:
                add_camera_lane_menu = QMenu("camera")
                for camera_action in camera_actions:
                    add_camera_lane_menu.addAction(camera_action)
                add_lane_menu.addMenu(add_camera_lane_menu)

        else:
            remove_lane_action = QAction("Remove")
            menu.addAction(remove_lane_action)
            # noinspection PyUnresolvedReferences
            remove_lane_action.triggered.connect(
                lambda: self._model.removeRow(index, QModelIndex())
            )

        menu.exec(self.lanes_view.verticalHeader().mapToGlobal(position))

    def create_digital_add_lane_actions(self):
        unused_channels = self._model.experiment_config.get_digital_channels()
        in_use_channels = self._model.shot_config.get_lane_names()
        possible_channels = list(unused_channels.difference(in_use_channels))
        possible_channels.sort()
        actions = [QAction(channel) for channel in possible_channels]
        for action in actions:
            # noinspection PyUnresolvedReferences
            action.triggered.connect(
                partial(
                    self._model.insert_lane,
                    self._model.rowCount(),
                    DigitalLane,
                    action.text(),
                )
            )
        return actions

    def create_analog_add_lane_actions(self):
        unused_channels = self._model.experiment_config.get_analog_channels()
        in_use_channels = self._model.shot_config.get_lane_names()
        possible_channels = list(unused_channels.difference(in_use_channels))
        possible_channels.sort()
        actions = [QAction(channel) for channel in possible_channels]
        for action in actions:
            # noinspection PyUnresolvedReferences
            action.triggered.connect(
                partial(
                    self._model.insert_lane,
                    self._model.rowCount(),
                    AnalogLane,
                    action.text(),
                )
            )
        return actions

    def create_camera_add_lane_actions(self):
        unused_cameras = self._model.experiment_config.get_cameras()
        in_use_channels = self._model.shot_config.get_lane_names()
        possible_channels = list(unused_cameras.difference(in_use_channels))
        possible_channels.sort()
        actions = [QAction(channel) for channel in possible_channels]
        for action in actions:
            # noinspection PyUnresolvedReferences
            action.triggered.connect(
                partial(
                    self._model.insert_lane,
                    self._model.rowCount(),
                    CameraLane,
                    action.text(),
                )
            )
        return actions

    def show_steps_context_menu(self, position):
        """Show the context menu on the step header to remove or add a new time step"""
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return

        menu = QMenu(self.steps_view.horizontalHeader())

        index = self.steps_view.horizontalHeader().logicalIndexAt(position)
        if index == -1:  # inserts a step after all steps
            add_step_action = QAction("Insert after")
            menu.addAction(add_step_action)
            # noinspection PyUnresolvedReferences
            add_step_action.triggered.connect(
                lambda: self._model.insertColumn(
                    self._model.columnCount(), QModelIndex()
                )
            )
        else:
            add_step_before_action = QAction("Insert before")
            menu.addAction(add_step_before_action)
            # noinspection PyUnresolvedReferences
            add_step_before_action.triggered.connect(
                lambda: self._model.insertColumn(index, QModelIndex())
            )

            add_step_after_action = QAction("Insert after")
            menu.addAction(add_step_after_action)
            # noinspection PyUnresolvedReferences
            add_step_after_action.triggered.connect(
                lambda: self._model.insertColumn(index + 1, QModelIndex())
            )

            remove_step_action = QAction("Remove")
            menu.addAction(remove_step_action)
            # noinspection PyUnresolvedReferences
            remove_step_action.triggered.connect(
                lambda: self._model.removeColumn(index, QModelIndex())
            )

        menu.exec(self.steps_view.horizontalHeader().mapToGlobal(position))

    def show_lane_cells_context_menu(self, position):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
        menu = QMenu(self.lanes_view.viewport())

        index = self.lanes_view.indexAt(position)
        if index.isValid():
            if len(self.lanes_view.selectionModel().selectedIndexes()) > 1:
                merge_action = QAction("Merge")
                menu.addAction(merge_action)
                # noinspection PyUnresolvedReferences
                merge_action.triggered.connect(
                    lambda: self._model.merge(
                        self.lanes_view.selectionModel().selectedIndexes()
                    )
                )
                break_action = QAction("Break")
                menu.addAction(break_action)
                # noinspection PyUnresolvedReferences
                break_action.triggered.connect(
                    lambda: self._model.break_(
                        self.lanes_view.selectionModel().selectedIndexes()
                    )
                )
            if isinstance(self._model.get_lane(index), CameraLane):
                camera_action = self._model.data(index, Qt.ItemDataRole.DisplayRole)
                if camera_action is None:
                    take_picture_action = QAction("Take picture")
                    menu.addAction(take_picture_action)
                    # noinspection PyUnresolvedReferences
                    take_picture_action.triggered.connect(
                        lambda: self._model.setData(
                            index,
                            TakePicture(picture_name="..."),
                            Qt.ItemDataRole.EditRole,
                        )
                    )
                elif isinstance(camera_action, str):
                    remove_picture_action = QAction("Remove picture")
                    menu.addAction(remove_picture_action)
                    # noinspection PyUnresolvedReferences
                    remove_picture_action.triggered.connect(
                        lambda: self._model.setData(
                            index,
                            None,
                            Qt.ItemDataRole.EditRole,
                        )
                    )

        menu.exec(self.lanes_view.viewport().mapToGlobal(position))
