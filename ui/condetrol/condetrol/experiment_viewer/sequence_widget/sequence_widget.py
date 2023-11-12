"""This module implements an editor for the configuration of a sequence.

It provides a pseudocode editor for the different steps of the sequence. The only role
of this module is to generate and edit a yaml file that is then consumed by other parts.
"""

import logging
from copy import deepcopy
from typing import Optional

from PyQt6.QtCore import (
    QModelIndex,
    Qt,
    QMimeData,
    QAbstractItemModel,
)
from PyQt6.QtGui import QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import (
    QDockWidget,
    QTreeView,
    QAbstractItemView,
    QTabWidget,
    QMenu,
)

from concurrent_updater.sequence_state_watcher import SequenceStateWatcher
from condetrol.utils import UndoStack
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker, ExperimentSession
from expression import Expression
from sequence.configuration import (
    Step,
    VariableDeclaration,
    ArangeLoop,
    LinspaceLoop,
    ExecuteShot,
    OptimizationLoop,
    UserInputLoop,
)
from sequence.runtime import Sequence, State
from settings_model import YAMLSerializable
from yaml_clipboard_mixin import YAMLClipboardMixin
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
        self._edit_session = session_maker()

        with self._session as session:
            sequence_config = self._sequence.get_config(session)

        self._sequence_program = sequence_config.program

        self.undo_stack = UndoStack()
        self.undo_stack.push(YAMLSerializable.dump(self._sequence_program))

        self._state_updater = SequenceStateWatcher(
            sequence, session_maker, watch_interval=0.5
        )
        self._state_updater.start()
        self.destroyed.connect(self._state_updater.stop)

    @property
    def sequence_state(self) -> State:
        return self._state_updater.sequence_state

    @property
    def program(self):
        return self._sequence_program

    def get_sequence_state(self, session: Optional[ExperimentSession]) -> State:
        if session is None:
            return self.sequence_state
        return self._sequence.get_state(session)

    @property
    def root(self):
        return self._sequence_program

    def save_config(self, session: ExperimentSession, save_undo: bool = True):
        self._sequence.set_steps_program(self._sequence_program, session)
        if save_undo:
            self.undo_stack.push(YAMLSerializable.dump(self._sequence_program))

    def setData(self, index: QModelIndex, values: dict[str], role: int = ...) -> bool:
        with self._edit_session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                if result := super().setData(index, values, role):
                    self.save_config(session)
                return result
            else:
                return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = super().flags(index)
            if self.sequence_state == State.DRAFT:
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
                new_steps = YAMLSerializable.load(new_yaml)

                self.beginResetModel()
                self._sequence_program = new_steps
                self.save_config(session, save_undo=False)
                self.endResetModel()
                self.layoutChanged.emit()

    def redo(self):
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                new_yaml = self.undo_stack.redo()
                new_steps = YAMLSerializable.load(new_yaml)
                self.beginResetModel()
                self._sequence_program = new_steps
                self.save_config(session, save_undo=False)
                self.endResetModel()
                self.layoutChanged.emit()

    def set_steps(self, steps: list[Step]):
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                super().set_steps(steps)
                self.save_config(session)


class SequenceTreeView(QTreeView, YAMLClipboardMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.expandAll()
        delegate = StepDelegate()
        self.setItemDelegate(delegate)
        self.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        # noinspection PyUnresolvedReferences

        self.setItemsExpandable(False)

        self.customContextMenuRequested.connect(self.show_context_menu)

    def setModel(self, model: QAbstractItemModel):
        super().setModel(model)
        self.model().rowsInserted.connect(lambda _: self.expandAll())
        self.expandAll()

    def convert_to_external_use(self):
        # noinspection PyTypeChecker
        model: SequenceStepsModel = self.model()
        return model.program.children

    def update_from_external_source(self, steps: list[Step]):
        # noinspection PyTypeChecker
        model: SequenceStepsModel = self.model()
        model.set_steps(steps)

    def show_context_menu(self, position):
        index = self.indexAt(position)
        # noinspection PyTypeChecker
        model: SequenceStepsModel = self.model()
        if model.get_sequence_state(None) != State.DRAFT:
            return

        menu = QMenu(self)

        add_menu = QMenu()
        add_menu.setTitle("Add...")
        menu.addMenu(add_menu)

        create_variable_action = QAction("Variable")
        add_menu.addAction(create_variable_action)
        # noinspection PyUnresolvedReferences
        create_variable_action.triggered.connect(
            lambda: model.insert_step(
                VariableDeclaration(name="new_variable", expression=Expression("...")),
                index,
            )
        )

        create_shot_action = QAction("Shot")
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

        create_linspace_action = QAction("Linspace loop")
        add_menu.addAction(create_linspace_action)
        # noinspection PyUnresolvedReferences
        create_linspace_action.triggered.connect(
            lambda: model.insert_step(
                LinspaceLoop(
                    name="new_variable",
                    start=Expression("..."),
                    stop=Expression("..."),
                    num=10,
                ),
                index,
            )
        )

        create_arange_action = QAction("Arange loop")
        add_menu.addAction(create_arange_action)
        # noinspection PyUnresolvedReferences
        create_arange_action.triggered.connect(
            lambda: model.insert_step(
                ArangeLoop(
                    name="new_variable",
                    start=Expression("..."),
                    stop=Expression("..."),
                    step=Expression("..."),
                ),
                index,
            )
        )

        optimization_menu = QMenu()
        optimization_menu.setTitle("Optimization loop...")
        add_menu.addMenu(optimization_menu)

        create_bayesian_optimization_action = QAction("Bayesian")
        optimization_menu.addAction(create_bayesian_optimization_action)
        create_bayesian_optimization_action.triggered.connect(
            lambda: model.insert_step(
                OptimizationLoop.empty_loop(),
                index,
            )
        )

        create_human_optimization_action = QAction("Human")
        optimization_menu.addAction(create_human_optimization_action)
        create_human_optimization_action.triggered.connect(
            lambda: model.insert_step(
                UserInputLoop.empty_loop(),
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

        menu.exec(self.mapToGlobal(position))


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
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._sequence = sequence
        self._experiment_config = experiment_config
        self._session_maker = session_maker

        self.tab_widget = QTabWidget()
        self.setWidget(self.tab_widget)

        self.program_tree = self.create_sequence_tree()
        self.tab_widget.addTab(self.program_tree, "Sequence")

        self.shot_widget = self.create_shot_widget()
        self.tab_widget.addTab(self.shot_widget, "Shot")

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)

        self._state_updater = SequenceStateWatcher(
            sequence,
            session_maker,
            on_state_changed=self.update_title,
            watch_interval=0.5,
        )
        self._state_updater.start()
        self.destroyed.connect(self._state_updater.stop)

    def update_title(self, state: State):
        self.setWindowTitle(f"{str(self._sequence.path)} [{state.name}]")

    def undo(self):
        self.program_tree.model().undo()

    def redo(self):
        self.program_tree.model().redo()

    @property
    def _session(self):
        return self._session_maker

    def create_sequence_tree(self):
        tree = SequenceTreeView()
        program_model = SequenceStepsModel(
            self._sequence, self._session_maker, parent=tree
        )
        tree.setModel(program_model)
        program_model.modelReset.connect(lambda: self.program_tree.expandAll())
        program_model.rowsInserted.connect(lambda _: tree.expandAll())
        return tree

    def create_shot_widget(self):
        w = ShotWidget(
            self._sequence, deepcopy(self._experiment_config), self._session_maker
        )
        return w

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.shot_widget.update_experiment_config(new_config)
