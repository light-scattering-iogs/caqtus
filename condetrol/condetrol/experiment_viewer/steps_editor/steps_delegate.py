import copy
import logging
from abc import abstractmethod
from functools import singledispatch

from PyQt6.QtCore import QModelIndex, Qt, QAbstractItemModel, QSize, QAbstractTableModel
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QWidget, QStyledItemDelegate, QStyleOptionViewItem, QStyle

from expression import Expression
from sequence.configuration import (
    Step,
    ArangeLoop,
    LinspaceLoop,
    VariableDeclaration,
    ExecuteShot,
    OptimizationLoop,
    OptimizationVariableInfo,
)
from .step_uis import (
    Ui_ArangeDeclaration,
    Ui_VariableDeclaration,
    Ui_LinspaceDeclaration,
    Ui_ExecuteShot,
    Ui_OptimizationDeclaration,
)
from .steps_model import QABCMeta

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
        editor.setAutoFillBackground(True)
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
        geometry = option.rect
        editor.setGeometry(geometry)

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
            pixmap.fill(option.palette.base().color())
            w = create_editor(data, option.widget)
            w.set_step_data(data)
            self.updateEditorGeometry(w, option, index)
            if not (option.state & QStyle.StateFlag.State_Enabled):
                w.setEnabled(False)
            w.render(pixmap, flags=QWidget.RenderFlag.DrawChildren)
            painter.drawPixmap(option.rect, pixmap)
        else:
            super().paint(painter, option, index)


class VariableDeclarationWidget(Ui_VariableDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

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


class OptimizationIterationWidget(Ui_OptimizationDeclaration, StepWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.variables_view.verticalHeader().setHidden(True)
        self.variables_view.resizeColumnToContents(0)
        self.optimizer_combobox.setEnabled(False)

    def set_step_data(self, data: OptimizationLoop):
        self.repetition_spin_box.setValue(data.repetitions)
        self.variables_view.setModel(VariableOptimizationModel(data.variables))
        self.optimizer_combobox.addItem(data.optimizer_name)

    def get_step_data(self):
        return dict(
            repetitions=self.repetition_spin_box.value(),
            variables=self.variables_view.model().variables,
        )


class VariableOptimizationModel(QAbstractTableModel):
    def __init__(self, variables: list[OptimizationVariableInfo]):
        super().__init__()
        self._variables = copy.deepcopy(variables)

    @property
    def variables(self):
        return self._variables

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._variables)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 4

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self._variables[index.row()]["name"]
            elif index.column() == 1:
                return self._variables[index.row()]["first_bound"].body
            elif index.column() == 2:
                return self._variables[index.row()]["second_bound"].body
            elif index.column() == 3:
                return self._variables[index.row()]["initial_value"].body
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            if section == 0:
                return "Variable"
            elif section == 1:
                return "From"
            elif section == 2:
                return "To"
            elif section == 3:
                return "Initial value"
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                self._variables[index.row()]["name"] = value
            elif index.column() == 1:
                self._variables[index.row()]["first_bound"] = Expression(value)
            elif index.column() == 2:
                self._variables[index.row()]["second_bound"] = Expression(value)
            elif index.column() == 3:
                self._variables[index.row()]["initial_value"] = Expression(value)
            self.dataChanged.emit(index, index)
            return True
        return False


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


@create_editor.register
def _(_: OptimizationLoop, parent: QWidget):
    return OptimizationIterationWidget(parent)
