"""This module implements an editor for the configuration of a sequence.

It provides a pseudocode editor for the different steps of the sequence. The only role
of this module is to generate and edit a yaml file that is then consumed by other parts.
"""

import logging
from copy import deepcopy

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
from experiment_session import ExperimentSessionMaker, ExperimentSession
from expression import Expression
from sequence.configuration import (
    Step,
    SequenceSteps,
    VariableDeclaration,
    ArangeLoop,
    LinspaceLoop,
    ExecuteShot,
)
from sequence.runtime import Sequence
from sequence.runtime.state import State
from .shot_widget import ShotWidget
from ..steps_editor import StepDelegate
from ..steps_editor import StepsModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SequenceStepsModel(StepsModel):
    """Model for a view to display and manipulate the steps of a sequence

    This model becomes read only if the sequence is not a draft, and it also saves any
    change.
    """

    def __init__(
        self, sequence: Sequence, session_maker: ExperimentSessionMaker, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self._sequence = sequence
        self._session = session_maker()

        with self._session as session:
            self.config = self._sequence.get_config(session)

        self.undo_stack = UndoStack()
        self.undo_stack.push(self.config.program.to_yaml())

    def get_sequence_state(self, session) -> State:
        return self._sequence.get_state(session)

    @property
    def root(self):
        return self.config.program

    def save_config(self, session: ExperimentSession, save_undo: bool = True):
        self._sequence.set_config(self.config, session)
        if save_undo:
            self.undo_stack.push(self.config.program.to_yaml())

    def setData(self, index: QModelIndex, values: dict[str], role: int = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                if result := super().setData(index, values, role):
                    self.save_config(session)
                return result
            else:
                return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = super().flags(index)
            with self._session as session:
                if self.get_sequence_state(session) == State.DRAFT:
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
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
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
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                if result := super().dropMimeData(data, action, row, column, parent):
                    self.save_config(session)
                return result
            else:
                return False

    def insert_step(self, new_step: Step, index: QModelIndex):
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                super().insert_step(new_step, index)
                self.save_config(session)

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                if result := super().removeRows(row, count, parent):
                    self.save_config(session)
                return result
            else:
                return False

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                if result := super().removeRow(row, parent):
                    self.save_config(session)
                return result
            else:
                return False

    def undo(self):
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                new_yaml = self.undo_stack.undo()
                new_steps = SequenceSteps.from_yaml(new_yaml)

                self.beginResetModel()
                self.config.program = new_steps
                self.save_config(session, save_undo=False)
                self.endResetModel()
                self.layoutChanged.emit()

    def redo(self):
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                new_yaml = self.undo_stack.redo()
                new_steps = SequenceSteps.from_yaml(new_yaml)
                self.beginResetModel()
                self.config.program = new_steps
                self.save_config(session, save_undo=False)
                self.endResetModel()
                self.layoutChanged.emit()


class SequenceWidget(QDockWidget):
    """Dockable widget that shows the sequence steps and shot"""

    def __init__(
        self,
        sequence: Sequence,
        experiment_config: ExperimentConfig,
        session_maker: ExperimentSessionMaker,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._sequence = sequence
        self._experiment_config = experiment_config
        self._session_maker = session_maker
        self.setWindowTitle(f"{str(self._sequence.path)}")

        self.tab_widget = QTabWidget()
        self.setWidget(self.tab_widget)

        self.program_tree = self.create_sequence_tree()
        # noinspection PyUnresolvedReferences
        self.program_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tab_widget.addTab(self.program_tree, "Sequence")

        self.shot_widget = self.create_shot_widget()
        self.tab_widget.addTab(self.shot_widget, "Shot")

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)

    def undo(self):
        self.program_tree.model().undo()

    def redo(self):
        self.program_tree.model().redo()

    @property
    def _session(self):
        return self._session_maker

    def create_sequence_tree(self):
        tree = QTreeView()
        tree.setHeaderHidden(True)
        tree.setAnimated(True)
        tree.setContentsMargins(0, 0, 0, 0)
        program_model = SequenceStepsModel(self._sequence, self._session_maker)
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
        # noinspection PyUnresolvedReferences
        tree.model().rowsInserted.connect(lambda _: tree.expandAll())

        tree.setItemsExpandable(False)
        return tree

    def show_context_menu(self, position):
        index = self.program_tree.indexAt(position)
        # noinspection PyTypeChecker
        model: SequenceStepsModel = self.program_tree.model()
        with self._session() as session:
            state = self._sequence.get_state(session)
        if state == State.DRAFT:

            menu = QMenu(self.program_tree)

            add_menu = QMenu()
            add_menu.setTitle("Add...")
            menu.addMenu(add_menu)

            create_variable_action = QAction("variable")
            add_menu.addAction(create_variable_action)
            # noinspection PyUnresolvedReferences
            create_variable_action.triggered.connect(
                lambda: model.insert_step(
                    VariableDeclaration(name="", expression=Expression("...")), index
                )
            )

            create_shot_action = QAction("shot")
            add_menu.addAction(create_shot_action)
            # noinspection PyUnresolvedReferences
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
            # noinspection PyUnresolvedReferences
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
            # noinspection PyUnresolvedReferences
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
                # noinspection PyUnresolvedReferences
                delete_action.triggered.connect(
                    lambda: model.removeRow(index.row(), index.parent())
                )

            menu.exec(self.program_tree.mapToGlobal(position))

    def create_shot_widget(self):
        w = ShotWidget(
            self._sequence, deepcopy(self._experiment_config), self._session_maker
        )
        return w

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.shot_widget.update_experiment_config(new_config)
