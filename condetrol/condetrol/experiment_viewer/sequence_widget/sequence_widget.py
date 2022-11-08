"""This module implements an editor for the configuration of a sequence.

It provides a pseudo-code editor for the different steps of the sequence. The only role
of this module is to generate and edit a yaml file that is then consumed by other parts.
"""

import logging
from abc import abstractmethod
from functools import singledispatch
from pathlib import Path

import yaml
from PyQt5.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QSize,
    QObject,
    pyqtSignal,
    QThread,
    QMimeData,
)
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import (
    QDockWidget,
    QTreeView,
    QStyledItemDelegate,
    QWidget,
    QStyleOptionViewItem,
    QStyle,
    QAbstractItemView,
    QTabWidget,
    QMenu,
    QAction,
)

from experiment_config import ExperimentConfig
from expression import Expression
from sequence import (
    Step,
    VariableDeclaration,
    SequenceStats,
    SequenceState,
    LinspaceLoop,
)
from sequence.sequence_config import ArangeLoop, ExecuteShot
from settings_model.settings_model import YAMLSerializable
from .sequence_watcher import SequenceWatcher
from .shot_widget import ShotWidget
from .step_uis import (
    Ui_ArangeDeclaration,
    Ui_VariableDeclaration,
    Ui_LinspaceDeclaration,
    Ui_ExecuteShot,
)
from .steps_model import StepsModel, QABCMeta

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class StepWidget(QWidget, metaclass=QABCMeta):
    """Abstract class for a widget used to display/edit a sequence step"""

    @abstractmethod
    def set_step_data(self, data: Step):
        raise NotImplementedError()

    @abstractmethod
    def get_step_data(self) -> dict[str]:
        raise NotImplementedError()


class VariableDeclarationWidget(Ui_VariableDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, declaration: VariableDeclaration):
        self.name_edit.setText(declaration.name)
        self.expression_edit.setText(declaration.expression.body)

    def get_step_data(self) -> dict[str]:
        return dict(
            name=self.name_edit.text(),
            expression=Expression(self.expression_edit.text()),
        )


class ExecuteShotWidget(Ui_ExecuteShot, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, shot: ExecuteShot):
        self.name_edit.setText(shot.name)

    def get_step_data(self) -> dict[str]:
        return dict(
            name=self.name_edit.text(),
        )


class LinspaceIterationWidget(Ui_LinspaceDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, data: LinspaceLoop):
        self.name_edit.setText(data.name)
        self.start_edit.setText(data.start.body)
        self.stop_edit.setText(data.stop.body)
        self.num_edit.setValue(data.num)

    def get_step_data(self):
        return dict(
            name=self.name_edit.text(),
            start=Expression(self.start_edit.text()),
            stop=Expression(self.stop_edit.text()),
            num=self.num_edit.value(),
        )


class ArangeIterationWidget(Ui_ArangeDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAutoFillBackground(True)

    def set_step_data(self, data: ArangeLoop):
        self.name_edit.setText(data.name)
        self.start_edit.setText(data.start.body)
        self.stop_edit.setText(data.stop.body)
        self.step_edit.setText(data.step.body)

    def get_step_data(self):
        return dict(
            name=self.name_edit.text(),
            start=Expression(self.start_edit.text()),
            stop=Expression(self.stop_edit.text()),
            step=Expression(self.step_edit.text()),
        )


@singledispatch
def create_editor(step: Step, _: QWidget) -> StepWidget:
    """Create an editor for a step depending on its type"""
    raise NotImplementedError(f"Not implemented for {type(step)}")


@create_editor.register
def _(_: VariableDeclaration, parent: QWidget):
    return VariableDeclarationWidget(parent)


@create_editor.register
def _(_: ExecuteShot, parent: QWidget):
    return ExecuteShotWidget(parent)


@create_editor.register
def _(_: LinspaceLoop, parent: QWidget):
    return LinspaceIterationWidget(parent)


@create_editor.register
def _(_: ArangeLoop, parent: QWidget):
    return ArangeIterationWidget(parent)


class StepDelegate(QStyledItemDelegate):
    """Delegate for a sequence step (see PyQt Model/View/Delegate)

    This delegate creates a widget editor to edit the data of a step. It also paints the
    widget on the view when editing if done.
    """

    def createEditor(
            self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> StepWidget:
        data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        # noinspection PyTypeChecker
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
        # noinspection PyTypeChecker
        w = create_editor(step, None)
        self.setEditorData(w, index)
        w.resize(option.rect.size())
        return w.sizeHint()

    def paint(
            self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        data = index.data(Qt.ItemDataRole.DisplayRole)
        if isinstance(data, Step):
            pixmap = QPixmap(option.rect.size())
            if option.state & QStyle.StateFlag.State_Selected:
                pixmap.fill(option.palette.highlight().color())
            else:
                pixmap.fill(option.palette.base().color())

            if not (option.state & QStyle.StateFlag.State_Editing):
                w = create_editor(data, option.widget)
                w.set_step_data(data)
                self.updateEditorGeometry(w, option, index)
                if not (option.state & QStyle.StateFlag.State_Enabled):
                    w.setEnabled(False)

                w.render(pixmap, flags=QWidget.RenderFlag.DrawChildren)
            else:
                logger.debug("editing")
            painter.drawPixmap(option.rect, pixmap)
        else:
            super().paint(painter, option, index)


class SequenceStepsModel(StepsModel):
    """Model for a view to display and manipulate the steps of a sequence

    This model becomes read only if the sequence is not a draft and it also saves any change to disk.
    """
    def __init__(self, sequence_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sequence_watcher = SequenceWatcher(sequence_path)
        self.config = self.sequence_watcher.read_config()
        self.sequence_state = self.sequence_watcher.read_stats().state

        self.sequence_watcher.config_changed.connect(self.change_sequence_config)
        self.sequence_watcher.stats_changed.connect(self.change_sequence_state)

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
        self.endResetModel()

    def save_config(self) -> bool:
        with self.sequence_watcher.block_signals():
            YAMLSerializable.dump(self.config, self.sequence_watcher.config_path)
            return True

    def setData(self, index: QModelIndex, values: dict[str], role: int = ...) -> bool:
        if self.sequence_state == SequenceState.DRAFT:
            if super().setData(index, values, role):
                self.save_config()
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = super().flags(index)
            if self.sequence_state == SequenceState.DRAFT:
                flags |= Qt.ItemFlag.ItemIsEditable
                if not isinstance(
                        self.data(index, Qt.ItemDataRole.DisplayRole),
                        VariableDeclaration,
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
                    VariableDeclaration(name="", expression=Expression()), index
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
                        name="", start=Expression(), stop=Expression(), num=10
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
                        start=Expression(),
                        stop=Expression(),
                        step=Expression(),
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
