import logging
from abc import abstractmethod, ABCMeta
from functools import singledispatchmethod, singledispatch
from pathlib import Path
from typing import Optional

import yaml
from PyQt5.QtCore import (
    QFileSystemWatcher,
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QSize,
    QObject,
    pyqtSignal,
    QThread,
)
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import (
    QDockWidget,
    QTreeView,
    QStyledItemDelegate,
    QWidget,
    QStyleOptionViewItem,
    QStyle, QAbstractItemView,
)

from condetrol.widgets import TreeNode
from sequence import (
    SequenceConfig,
    Step,
    StepsSequence,
    VariableDeclaration,
    SequenceStats,
    SequenceState,
    LinspaceIteration,
    ExecuteShot,
)
from .sequence_execute_shot_ui import Ui_ExecuteShot
from .sequence_linspace_iteration_ui import Ui_LinspaceDeclaration
from .sequence_variable_declaration_ui import Ui_VariableDeclaration

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class QABCMeta(type(QObject), ABCMeta):
    pass


class StepWidget(QWidget, metaclass=QABCMeta):
    """Abstract class for a widget used to display/edit a sequence step"""

    @abstractmethod
    def set_step_data(self, data: Step):
        raise NotImplementedError()

    @abstractmethod
    def get_step_data(self) -> Step:
        raise NotImplementedError()


class LinspaceIterationWidget(Ui_LinspaceDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, data: LinspaceIteration):
        self.name_edit.setText(data.name)
        self.start_edit.setText(data.start)
        self.stop_edit.setText(data.stop)
        self.num_edit.setValue(data.num)
        self.sub_steps = data.sub_steps

    def get_step_data(self) -> LinspaceIteration:
        return LinspaceIteration(
            name=self.name_edit.text(),
            start=self.start_edit.text(),
            stop=self.stop_edit.text(),
            num=self.num_edit.value(),
            sub_steps=self.sub_steps,
        )


class VariableDeclarationWidget(Ui_VariableDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, declaration: VariableDeclaration):
        self.name_edit.setText(declaration.name)
        self.expression_edit.setText(declaration.expression)

    def get_step_data(self) -> VariableDeclaration:
        return VariableDeclaration(
            name=self.name_edit.text(), expression=self.expression_edit.text()
        )


class ExecuteShotWidget(Ui_ExecuteShot, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, shot: ExecuteShot):
        self.name_edit.setText(shot.name)
        self.shot = shot

    def get_step_data(self) -> ExecuteShot:
        self.shot.name = self.name_edit.text()
        return self.shot


class StepTreeNode(TreeNode[Step]):
    """Implementation of a tree representation of a sequence

    This class is a helper for a recursive PyQt model (see PyQt Model/View). It allows
    to get the parent and children of a sequence step.
    """

    def get_children(self) -> list[TreeNode[Step]]:
        return self.get_step_children(self.internal_pointer)

    @singledispatchmethod
    def get_step_children(self, step) -> list[TreeNode[Step]]:
        """Generate the child nodes of a parent step"""
        raise NotImplementedError(f"Can't find the substeps of {type(step)}")

    @get_step_children.register
    def _(self, step: StepsSequence):
        return [
            StepTreeNode(sub_step, self, row) for row, sub_step in enumerate(step.steps)
        ]

    @get_step_children.register
    def _(self, step: LinspaceIteration):
        return [
            StepTreeNode(sub_step, self, row)
            for row, sub_step in enumerate(step.sub_steps)
        ]

    @get_step_children.register
    def _(self, step: VariableDeclaration):
        return []

    @get_step_children.register
    def _(self, step: ExecuteShot):
        return []

    @singledispatchmethod
    def update_value(self, new_value: Step):
        """Edit the parameters of a step

        This method should either update the internal pointer in place or either replace
        it with a new variable and update its parent as well.
        """
        raise NotImplementedError(f"Not implemented for {type(new_value)}")

    @update_value.register
    def _(self, new_value: VariableDeclaration):
        self.internal_pointer: VariableDeclaration
        self.internal_pointer.name = new_value.name
        self.internal_pointer.expression = new_value.expression

    @update_value.register
    def _(self, new_value: LinspaceIteration):
        self.internal_pointer: LinspaceIteration
        self.internal_pointer.name = new_value.name
        self.internal_pointer.start = new_value.start
        self.internal_pointer.stop = new_value.stop
        self.internal_pointer.num = new_value.num

    @update_value.register
    def _(self, new_value: ExecuteShot):
        self.internal_pointer: ExecuteShot
        self.internal_pointer.name = new_value.name

    @singledispatchmethod
    @classmethod
    def update_parent_data(
        cls, parent_step: Step, new_child_value: Step, child_row: int
    ):
        """Replace a child node of a parent node with a new value"""
        raise NotImplementedError()

    @update_parent_data.register
    @classmethod
    def _(cls, parent_step: StepsSequence, new_child_value: Step, child_row: int):
        parent_step.steps[child_row] = new_child_value

    @update_parent_data.register
    @classmethod
    def _(cls, parent_step: LinspaceIteration, new_child_value: Step, child_row: int):
        parent_step.sub_steps[child_row] = new_child_value


@singledispatch
def create_editor(step: Step, parent: QWidget) -> StepWidget:
    """Create an editor for a step depending on its type"""
    raise NotImplementedError


@create_editor.register
def _(step: VariableDeclaration, parent: QWidget):
    return VariableDeclarationWidget(parent)


@create_editor.register
def _(step: LinspaceIteration, parent: QWidget):
    return LinspaceIterationWidget(parent)


@create_editor.register
def _(step: ExecuteShot, parent: QWidget):
    return ExecuteShotWidget(parent)


class StepDelegate(QStyledItemDelegate):
    """Delegate for a sequence step (see PyQt Model/View/Delegate)

    This delegate creates a widget editor to edit the data of a step. It also paints the
    widget on the view when editing if done.
    """

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> StepWidget:
        data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        editor = create_editor(data, None)
        editor.setParent(parent)
        return editor

    def setEditorData(self, editor: StepWidget, index: QModelIndex):
        editor.set_step_data(index.data(role=Qt.ItemDataRole.EditRole))

    def setModelData(
        self, editor: StepWidget, model: QAbstractItemModel, index: QModelIndex
    ) -> None:
        model.setData(index, editor.get_step_data(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(
        self, editor: StepWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):
        editor.setGeometry(option.rect)

    def sizeHint(self, option: "QStyleOptionViewItem", index: QModelIndex) -> QSize:
        step = index.data(role=Qt.ItemDataRole.DisplayRole)
        w = create_editor(step, None)
        self.setEditorData(w, index)
        w.resize(option.rect.size())
        return w.sizeHint()

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        data = index.data(Qt.ItemDataRole.DisplayRole)
        if isinstance(data, Step):
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            w = create_editor(data, option.widget)
            w.set_step_data(data)
            self.updateEditorGeometry(w, option, index)
            if not (option.state & QStyle.StateFlag.State_Enabled):
                w.setEnabled(False)
            pixmap = QPixmap(option.rect.size())
            w.render(pixmap)
            painter.drawPixmap(option.rect, pixmap)
        else:
            super().paint(painter, option, index)


class FinishedSignal(QObject):
    finished = pyqtSignal()


class SaveThread(QThread):
    finished = pyqtSignal()

    def __init__(self, data: str, file: Path):
        super().__init__()
        self._data = data
        self._file = file

    def run(self):
        with open(self._file, "w") as file:
            file.write(self._data)
        self.finished.emit()


class StepsModel(QAbstractItemModel):
    """Qt Model for sequence steps (see PyQt Model/View)

    This model provides data for a view to display the different steps of a sequence. It
    watches and saves the sequence steps on the sequence_path/sequence_config.yaml file.
    It also watches the sequence_path/sequence_state.yaml file, and if the sequence
    state is not 'DRAFT', it sets the data to not editable.
    """

    def __init__(self, sequence_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_path = sequence_path / "sequence_config.yaml"
        self.state_path = sequence_path / "sequence_state.yaml"

        with open(self.config_path) as file:
            self.config: SequenceConfig = yaml.safe_load(file)
        self.root = StepTreeNode(self.config.program)
        self.layoutChanged.emit()

        self.sequence_config_watcher = QFileSystemWatcher()
        self.sequence_config_watcher.addPath(str(self.config_path))
        self.sequence_config_watcher.fileChanged.connect(self.change_sequence_config)

        self.sequence_state_watcher = QFileSystemWatcher()
        self.sequence_state_watcher.addPath(str(self.state_path))
        self.sequence_state_watcher.fileChanged.connect(self.change_sequence_state)
        self.sequence_state = SequenceState.DRAFT

        self.save_thread: Optional[SaveThread] = None

    def change_sequence_state(self, path):
        with open(path, "r") as file:
            stats: SequenceStats = yaml.safe_load(file)
        self.sequence_state = stats.state
        self.layoutChanged.emit()

    def change_sequence_config(self, sequence_config):
        with open(sequence_config) as file:
            self.config: SequenceConfig = yaml.safe_load(file)
        self.root = StepTreeNode(self.config.program)
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
        if not isinstance(child_node, StepTreeNode):
            logger.debug("danger")
            return QModelIndex()
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
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                return node.internal_pointer

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        edit = False
        if (
            index.isValid()
            and role == Qt.ItemDataRole.EditRole
            and self.sequence_state == SequenceState.DRAFT
        ):
            node: StepTreeNode = index.internalPointer()
            node.update_value(value)
            edit = True

        if edit:
            # save config to file in a new thread to avoid blocking the GUI
            self.sequence_config_watcher.removePath(str(self.config_path))
            self.config.program = self.root.internal_pointer
            serialized_config = yaml.safe_dump(self.config)
            if self.save_thread:
                self.save_thread.wait()
            self.save = SaveThread(serialized_config, self.config_path)
            self.save.finished.connect(
                lambda: self.sequence_config_watcher.addPath(str(self.config_path))
            )
            self.save.start()
            self.save.wait()
        return edit

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid():
            if index.column() == 0:
                flags = Qt.ItemFlag.ItemIsSelectable
                if self.sequence_state == SequenceState.DRAFT:
                    return (
                        flags | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled
                    )
                else:
                    return flags
        return Qt.ItemFlag.NoItemFlags


class SequenceWidget(QDockWidget):
    """Dockable widget that shows the sequence steps and shot"""

    def __init__(self, sequence_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = sequence_path
        self.setWindowTitle(f"{self._path}")

        self.program_tree = QTreeView()
        self.program_tree.setHeaderHidden(True)
        self.program_tree.setAnimated(True)
        self.program_tree.setContentsMargins(0, 0, 0, 0)
        self.program_model = StepsModel(self._path)
        self.program_tree.setModel(self.program_model)
        self.setWidget(self.program_tree)
        self.program_model.layoutChanged.connect(lambda: self.program_tree.expandAll())
        self.program_tree.expandAll()
        self.delegate = StepDelegate()
        self.program_tree.setItemDelegate(self.delegate)
        self.program_tree.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
