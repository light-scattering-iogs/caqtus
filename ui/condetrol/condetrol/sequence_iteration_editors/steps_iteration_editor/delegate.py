import re
from typing import Optional

from PyQt6.QtCore import QModelIndex, Qt, QAbstractItemModel
from PyQt6.QtGui import QValidator, QFont
from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QLineEdit,
    QWidget,
    QStyleOptionViewItem,
)

from core.session.sequence.iteration_configuration import (
    Step,
    VariableDeclaration,
    LinspaceLoop,
    ArangeLoop,
)
from core.types.expression import Expression
from core.types.variable_name import DOTTED_VARIABLE_NAME_REGEX, DottedVariableName
from core.types.expression import EXPRESSION_REGEX

VARIABLE_DECLARATION_REGEX = re.compile(
    f"(?P<variable>{DOTTED_VARIABLE_NAME_REGEX.pattern}) = (?P<value>{EXPRESSION_REGEX.pattern})"
)

LINSPACE_LOOP_REGEX = re.compile(
    f"for (?P<variable>{DOTTED_VARIABLE_NAME_REGEX.pattern}) "
    f"= (?P<start>{EXPRESSION_REGEX.pattern}) "
    f"to (?P<stop>{EXPRESSION_REGEX.pattern}) "
    f"with (?P<num>[0-9]+) steps:"
)

ARANGE_LOOP_REGEX = re.compile(
    f"for (?P<variable>{DOTTED_VARIABLE_NAME_REGEX.pattern}) "
    f"= (?P<start>{EXPRESSION_REGEX.pattern}) "
    f"to (?P<stop>{EXPRESSION_REGEX.pattern}) "
    f"with (?P<step>{EXPRESSION_REGEX.pattern}) spacing:"
)


class StepDelegate(QStyledItemDelegate):
    def __iter__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QLineEdit:
        editor = QLineEdit()
        editor.setParent(parent)
        font = QFont()
        font.setPixelSize(15)
        editor.setFont(font)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        editor: QLineEdit
        data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        match data:
            case VariableDeclaration(variable, value):
                text = f"{variable} = {value}"
                editor.setValidator(VariableDeclarationValidator())
            case LinspaceLoop(variable, start, stop, num, sub_steps):
                text = f"for {variable} = {start} to {stop} with {num} steps:"
                editor.setValidator(LinSpaceLoopValidator())
            case ArangeLoop(variable, start, stop, step, sub_steps):
                text = f"for {variable} = {start} to {stop} with {step} spacing:"
                editor.setValidator(ArangeLoopValidator())
        editor.setText(text)

    def setModelData(
        self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex
    ) -> None:
        editor: QLineEdit
        previous_data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        text = editor.text()
        match previous_data:
            case VariableDeclaration():
                match = VARIABLE_DECLARATION_REGEX.fullmatch(text)
                if match:
                    new_attributes = {
                        "variable": DottedVariableName(match.group("variable")),
                        "value": Expression(match.group("value")),
                    }
                    model.setData(index, new_attributes, Qt.ItemDataRole.EditRole)
            case LinspaceLoop():
                match = LINSPACE_LOOP_REGEX.fullmatch(text)
                if match:
                    new_attributes = {
                        "variable": DottedVariableName(match.group("variable")),
                        "start": Expression(match.group("start")),
                        "stop": Expression(match.group("stop")),
                        "num": int(match.group("num")),
                    }
                    model.setData(index, new_attributes, Qt.ItemDataRole.EditRole)
            case ArangeLoop():
                match = ARANGE_LOOP_REGEX.fullmatch(text)
                if match:
                    new_attributes = {
                        "variable": DottedVariableName(match.group("variable")),
                        "start": Expression(match.group("start")),
                        "stop": Expression(match.group("stop")),
                        "step": Expression(match.group("step")),
                    }
                    model.setData(index, new_attributes, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(
        self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):
        geometry = option.rect
        editor.setGeometry(geometry)


class VariableDeclarationValidator(QValidator):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def validate(self, input: str, pos: int) -> tuple[QValidator.State, str, int]:
        if VARIABLE_DECLARATION_REGEX.fullmatch(input):
            return QValidator.State.Acceptable, input, pos
        else:
            return QValidator.State.Invalid, input, pos


class LinSpaceLoopValidator(QValidator):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def validate(self, input: str, pos: int) -> tuple[QValidator.State, str, int]:
        if LINSPACE_LOOP_REGEX.fullmatch(input):
            return QValidator.State.Acceptable, input, pos
        else:
            return QValidator.State.Invalid, input, pos


class ArangeLoopValidator(QValidator):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def validate(self, input: str, pos: int) -> tuple[QValidator.State, str, int]:
        if ARANGE_LOOP_REGEX.fullmatch(input):
            return QValidator.State.Acceptable, input, pos
        else:
            return QValidator.State.Invalid, input, pos
