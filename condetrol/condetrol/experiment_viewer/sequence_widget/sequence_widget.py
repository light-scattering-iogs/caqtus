"""This module implements an editor for the configuration of a sequence.

It provides a pseudocode editor for the different steps of the sequence. The only role
of this module is to generate and edit a yaml file that is then consumed by other parts.
"""

import logging
from pathlib import Path

from PyQt6.QtCore import (
    QModelIndex,
    Qt,
    QMimeData,
)
from PyQt6.QtGui import QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import (
    QDockWidget,
    QTreeView,
    QAbstractItemView,
    QTabWidget,
    QMenu,
)

from condetrol.utils import UndoStack
from experiment_config import ExperimentConfig
from expression import Expression
from sequence import (
    Step,
    VariableDeclaration,
    SequenceStats,
    SequenceState,
    LinspaceLoop,
)
from sequence.sequence_config import ArangeLoop, ExecuteShot, SequenceSteps
from settings_model.settings_model import YAMLSerializable
from .sequence_watcher import SequenceWatcher
from .shot_widget import ShotWidget
from ..steps_editor import StepDelegate
from ..steps_editor import StepsModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SequenceStepsModel(StepsModel):
    """Model for a view to display and manipulate the steps of a sequence

    This model becomes read only if the sequence is not a draft, and it also saves any change to disk.
    """

    def __init__(self, sequence_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sequence_watcher = SequenceWatcher(sequence_path)
        self.config = self.sequence_watcher.read_config()
        self.sequence_state = self.sequence_watcher.read_stats().state

        self.sequence_watcher.config_changed.connect(self.change_sequence_config)
        self.sequence_watcher.stats_changed.connect(self.change_sequence_state)

        self.undo_stack = UndoStack()
        self.undo_stack.push(self.config.program.to_yaml())

    @property
    def root(self):
        return self.config.program

    def change_sequence_state(self, stats: SequenceStats):
        self.beginResetModel()
        self.sequence_state = stats.state
        self.endResetModel()

    def change_sequence_config(self, sequence_config):
        self.beginResetModel()
        self.config = sequence_config
        self.undo_stack.push(self.config.program.to_yaml())
        self.endResetModel()

    def save_config(self, save_undo: bool = True) -> bool:
        with self.sequence_watcher.block_signals():
            YAMLSerializable.dump(self.config, self.sequence_watcher.config_path)
            if save_undo:
                self.undo_stack.push(self.config.program.to_yaml())
            return True

    def setData(self, index: QModelIndex, values: dict[str], role: int = ...) -> bool:
        if self.sequence_state == SequenceState.DRAFT:
            if result := super().setData(index, values, role):
                self.save_config()
            return result
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = super().flags(index)
            if self.sequence_state == SequenceState.DRAFT:
                flags |= Qt.ItemFlag.ItemIsEditable
                if not isinstance(
                    self.data(index, Qt.ItemDataRole.DisplayRole),
                    (VariableDeclaration, ExecuteShot),
                ):
                    flags |= Qt.ItemFlag.ItemIsDropEnabled
        else:
            flags = Qt.ItemFlag.NoItemFlags
        return flags

    def supportedDragActions(self) -> Qt.DropAction:
        if self.sequence_state == SequenceState.DRAFT:
            return Qt.DropAction.MoveAction
        else:
            return Qt.DropAction.CopyAction

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if self.sequence_state == SequenceState.DRAFT:
            if result := super().dropMimeData(data, action, row, column, parent):
                self.save_config()
            return result
        else:
            return False

    def insert_step(self, new_step: Step, index: QModelIndex):
        if self.sequence_state == SequenceState.DRAFT:
            super().insert_step(new_step, index)
            self.save_config()

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        if self.sequence_state == SequenceState.DRAFT:
            if result := super().removeRows(row, count, parent):
                self.save_config()
            return result
        else:
            return False

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if self.sequence_state == SequenceState.DRAFT:
            if result := super().removeRow(row, parent):
                self.save_config()
            return result
        else:
            return False

    def undo(self):
        new_yaml = self.undo_stack.undo()
        new_steps = SequenceSteps.from_yaml(new_yaml)
        self.beginResetModel()
        self.config.program = new_steps
        self.save_config(save_undo=False)
        self.endResetModel()
        self.layoutChanged.emit()

    def redo(self):
        new_yaml = self.undo_stack.redo()
        new_steps = SequenceSteps.from_yaml(new_yaml)
        self.beginResetModel()
        self.config.program = new_steps
        self.save_config(save_undo=False)
        self.endResetModel()
        self.layoutChanged.emit()


class SequenceWidget(QDockWidget):
    """Dockable widget that shows the sequence steps and shot"""

    def __init__(
        self, sequence_path: Path, experiment_config_path: Path, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._path = sequence_path
        experiment_config: ExperimentConfig = YAMLSerializable.load(
            experiment_config_path
        )
        self.setWindowTitle(f"{self._path.relative_to(experiment_config.data_path)}")

        self.tab_widget = QTabWidget()
        self.setWidget(self.tab_widget)

        self.program_tree = self.create_sequence_tree()
        self.program_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tab_widget.addTab(self.program_tree, "Sequence")

        self.shot_widget = self.create_shot_widget(experiment_config_path)
        self.tab_widget.addTab(self.shot_widget, "Shot")

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)

    def undo(self):
        self.program_tree.model().undo()

    def redo(self):
        self.program_tree.model().redo()

    def create_sequence_tree(self):
        tree = QTreeView()
        tree.setHeaderHidden(True)
        tree.setAnimated(True)
        tree.setContentsMargins(0, 0, 0, 0)
        program_model = SequenceStepsModel(self._path)
        tree.setModel(program_model)
        program_model.modelReset.connect(lambda: self.program_tree.expandAll())
        tree.expandAll()
        delegate = StepDelegate()
        tree.setItemDelegate(delegate)
        tree.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)

        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        tree.setDragEnabled(True)
        tree.setAcceptDrops(True)
        tree.setDropIndicatorShown(True)
        tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        tree.setDragDropOverwriteMode(False)
        tree.model().rowsInserted.connect(lambda _: tree.expandAll())

        tree.setItemsExpandable(False)
        return tree

    def show_context_menu(self, position):
        index = self.program_tree.indexAt(position)
        # noinspection PyTypeChecker
        model: SequenceStepsModel = self.program_tree.model()
        if model.sequence_state == SequenceState.DRAFT:

            menu = QMenu(self.program_tree)

            add_menu = QMenu()
            add_menu.setTitle("Add...")
            menu.addMenu(add_menu)

            create_variable_action = QAction("variable")
            add_menu.addAction(create_variable_action)
            create_variable_action.triggered.connect(
                lambda: model.insert_step(
                    VariableDeclaration(name="", expression=Expression("...")), index
                )
            )

            create_shot_action = QAction("shot")
            add_menu.addAction(create_shot_action)
            create_shot_action.triggered.connect(
                lambda: model.insert_step(
                    ExecuteShot(
                        name="shot",
                    ),
                    index,
                )
            )

            create_linspace_action = QAction("linspace loop")
            add_menu.addAction(create_linspace_action)
            create_linspace_action.triggered.connect(
                lambda: model.insert_step(
                    LinspaceLoop(
                        name="", start=Expression("..."), stop=Expression("..."), num=10
                    ),
                    index,
                )
            )

            create_arange_action = QAction("arange loop")
            add_menu.addAction(create_arange_action)
            create_arange_action.triggered.connect(
                lambda: model.insert_step(
                    ArangeLoop(
                        name="",
                        start=Expression("..."),
                        stop=Expression("..."),
                        step=Expression("..."),
                    ),
                    index,
                )
            )

            if index.isValid():
                delete_action = QAction("Delete")
                menu.addAction(delete_action)
                delete_action.triggered.connect(
                    lambda: model.removeRow(index.row(), index.parent())
                )

            menu.exec(self.program_tree.mapToGlobal(position))

    def create_shot_widget(self, experiment_config_path):
        w = ShotWidget(self._path, experiment_config_path)
        return w

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.shot_widget.update_experiment_config(new_config)
