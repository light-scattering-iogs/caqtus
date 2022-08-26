import logging
from functools import singledispatchmethod, singledispatch
from pathlib import Path

import yaml
from PyQt5.QtCore import QFileSystemWatcher, QAbstractItemModel, QModelIndex, Qt, QSize, \
    QEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import (
    QDockWidget,
    QTreeView,
    QStyledItemDelegate,
    QWidget,
    QStyleOptionViewItem,
)
from condetrol.widgets import TreeNode
from sequence import (
    SequenceConfig,
    SequenceStats,
    SequenceState,
    Step,
    StepsSequence,
    VariableDeclaration,
)

from .sequence_variable_declaration_ui import Ui_VariableDeclaration

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class VariableDeclarationWidget(Ui_VariableDeclaration, QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # self.setAutoFillBackground(True)

    def set_data(self, declaration: VariableDeclaration):
        self.name_edit.setText(declaration.name)
        self.expression_edit.setText(declaration.expression)


class StepTreeNode(TreeNode[Step]):
    def get_children(self) -> list[TreeNode[Step]]:
        return self.get_step_children(self.internal_pointer)

    @singledispatchmethod
    def get_step_children(self, step: Step) -> list[TreeNode[Step]]:
        raise NotImplementedError("Can't find the substeps of the base class")

    @get_step_children.register
    def _(self, step: StepsSequence):
        return [
            StepTreeNode(sub_step, self, row) for row, sub_step in enumerate(step.steps)
        ]

    @get_step_children.register
    def _(self, step: VariableDeclaration):
        return []


@singledispatch
def create_editor(step: Step, parent: QWidget) -> QWidget:
    raise NotImplementedError


@create_editor.register
def _(step: VariableDeclaration, parent: QWidget):
    return VariableDeclarationWidget(parent)


class StepDelegate(QStyledItemDelegate):
    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):
        data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        editor = create_editor(data, parent)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        editor.set_data(index.data(role=Qt.ItemDataRole.EditRole))


    def updateEditorGeometry(
        self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):
        editor.setGeometry(option.rect)


class StepsModel(QAbstractItemModel):
    def __init__(self, config_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open(config_path) as file:
            config: SequenceConfig = yaml.safe_load(file)
        self.root = StepTreeNode(config.program)
        self.sequence_config_watcher = QFileSystemWatcher()
        self.sequence_config_watcher.addPath(str(config_path))
        self.sequence_config_watcher.fileChanged.connect(self.change_config)

    def change_config(self, sequence_config):
        with open(sequence_config) as file:
            config: SequenceConfig = yaml.safe_load(file)
        self.root = StepTreeNode(config.program)
        self.layoutChanged.emit()

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            current_node = self.root.children[row]
        else:
            parent_node: StepTreeNode = parent.internalPointer()
            if row < parent_node.child_count:
                current_node = parent_node.children[row]
            else:
                return QModelIndex()

        return self.createIndex(row, column, current_node)

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child_node: StepTreeNode = child.internalPointer()
        if child_node.parent:
            parent_node = child_node.parent
            return self.createIndex(parent_node.row, 0, parent_node)
        else:
            return QModelIndex()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if not parent.isValid():
            return self.root.child_count
        else:
            parent_node: TreeNode = parent.internalPointer()
            return parent_node.child_count

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = ...):
        if index.isValid():
            node: StepTreeNode = index.internalPointer()
            if role == Qt.ItemDataRole.DisplayRole:
                data = node.internal_pointer
                if isinstance(data, VariableDeclaration):
                    return f"{data.name} = {data.expression}"
                else:
                    return str(data)
            if role == Qt.ItemDataRole.EditRole:
                return node.internal_pointer
            if role == Qt.ItemDataRole.SizeHintRole:
                return QSize(300, 25)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.isValid():
            if index.column() == 0:
                return (
                    Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsEditable
                )
        return Qt.ItemFlag.NoItemFlags

class HoverTreeView(QTreeView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_index = None
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        current_index = self.indexAt(event.pos())
        if current_index != self._previous_index:
            if self._previous_index:
                self.closePersistentEditor(self._previous_index)
            self.openPersistentEditor(self.currentIndex())
            self._previous_index = current_index

    def leaveEvent(self, a0: QEvent) -> None:
        self.closePersistentEditor(self._previous_index)

class SequenceWidget(QDockWidget):
    def __init__(self, sequence_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = sequence_path
        self.setWindowTitle(f"{self._path}")

        self.sequence_state_watcher = QFileSystemWatcher()
        self.sequence_state_watcher.addPath(str(self._path / "sequence_state.yaml"))
        self.sequence_state_watcher.fileChanged.connect(self.lock_sequence)
        self.lock_sequence(str(self._path / "sequence_state.yaml"))

        self.program_tree = HoverTreeView()
        self.program_model = StepsModel(self._path / "sequence_config.yaml")
        self.program_tree.setModel(self.program_model)
        self.setWidget(self.program_tree)
        self.program_tree.expandAll()
        self.delegate = StepDelegate()
        self.program_tree.setItemDelegate(self.delegate)

    def lock_sequence(self, sequence_stats):
        with open(sequence_stats) as file:
            stats: SequenceStats = yaml.safe_load(file)
            self.setEnabled(stats.state == SequenceState.DRAFT)
