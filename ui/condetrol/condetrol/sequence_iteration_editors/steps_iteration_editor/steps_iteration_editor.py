import functools
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QFont
from PyQt6.QtWidgets import QWidget, QTreeView, QAbstractItemView, QMenu

from core.session.sequence.iteration_configuration import (
    StepsConfiguration,
    VariableDeclaration,
    ExecuteShot,
    LinspaceLoop,
    ArangeLoop,
)
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from .steps_model import StepsModel
from ..sequence_iteration_editor import SequenceIterationEditor


def create_variable_declaration():
    return VariableDeclaration(
        variable=DottedVariableName("new_variable"), value=Expression("...")
    )


def create_linspace_loop():
    return LinspaceLoop(
        variable=DottedVariableName("new_variable"),
        start=Expression("..."),
        stop=Expression("..."),
        num=10,
        sub_steps=[],
    )


def create_arange_loop():
    return ArangeLoop(
        variable=DottedVariableName("new_variable"),
        start=Expression("..."),
        stop=Expression("..."),
        step=Expression("..."),
        sub_steps=[],
    )


class StepsIterationEditor(QTreeView, SequenceIterationEditor[StepsConfiguration]):
    def __init__(self, iteration: StepsConfiguration, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.iteration = iteration
        self.read_only = False
        self._model = StepsModel(iteration)
        self.setModel(self._model)
        self.expandAll()
        self.header().hide()

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        # self.setDragDropOverwriteMode(False)

        self.delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        self.delete_shortcut.activated.connect(self.delete_selected)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        font = QFont()
        font.setPixelSize(15)
        self.setFont(font)

    def get_iteration(self) -> StepsConfiguration:
        return self.iteration

    def set_iteration(self, iteration: StepsConfiguration):
        self.iteration = iteration

    def set_read_only(self, read_only: bool):
        self.read_only = read_only

    def delete_selected(self):
        selected = self.selectedIndexes()
        if selected:
            self._model.removeRow(selected[0].row(), selected[0].parent())

    def show_context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu(self)

        add_menu = QMenu()
        add_menu.setTitle("Insert above...")
        menu.addMenu(add_menu)

        create_variable_action = QAction("variable")
        add_menu.addAction(create_variable_action)
        new_variable = create_variable_declaration()
        create_variable_action.triggered.connect(
            functools.partial(self._model.insert_above, new_variable, index)
        )
        create_shot_action = QAction("Shot")
        add_menu.addAction(create_shot_action)
        new_shot = ExecuteShot()
        create_shot_action.triggered.connect(
            functools.partial(self._model.insert_above, new_shot, index)
        )
        create_linspace_action = QAction("Linspace loop")
        add_menu.addAction(create_linspace_action)
        new_linspace = create_linspace_loop()
        create_linspace_action.triggered.connect(
            functools.partial(self._model.insert_above, new_linspace, index)
        )
        create_arange_action = QAction("Arange loop")
        add_menu.addAction(create_arange_action)
        new_arange = create_arange_loop()
        create_arange_action.triggered.connect(
            functools.partial(self._model.insert_above, new_arange, index)
        )
        menu.exec(self.mapToGlobal(position))
