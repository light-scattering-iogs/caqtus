import re
from typing import Optional, assert_never

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QModelIndex, Qt, QRectF, QAbstractItemModel
from PySide6.QtGui import (
    QValidator,
    QTextDocument,
    QAbstractTextDocumentLayout,
)
from PySide6.QtWidgets import (
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
    ImportConstantTable,
    ExecuteShot,
)
from core.types.expression import EXPRESSION_REGEX
from core.types.expression import Expression
from core.types.variable_name import DOTTED_VARIABLE_NAME_REGEX, DottedVariableName
from ...qt_util import AutoResizeLineEdit

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

IMPORT_CONSTANT_TABLE_REGEX = re.compile(
    f"import (?P<table>{DOTTED_VARIABLE_NAME_REGEX.pattern})"
    f"( as (?P<alias>{DOTTED_VARIABLE_NAME_REGEX.pattern}))?"
)


def to_str(step: Step) -> str:
    hl = "#cc7832"
    var_col = "#AA4926"
    val_col = "#6897BB"
    text_col = "#FFFFFF"
    match step:
        case ExecuteShot():
            return f"<span style='color:{hl}'>do shot</span>"
        case VariableDeclaration(variable, value):
            return (
                f"<span style='color:{var_col}'>{variable}</span> "
                "<span style='color:#FFFFFF'>=</span> "
                f"<span style='color:{val_col}'>{value}</span>"
            )
        case ArangeLoop(variable, start, stop, step, sub_steps):
            return (
                f"<span style='color:{hl}'>for</span> "
                f"<span style='color:{var_col}'>{variable}</span> "
                "<span style='color:#FFFFFF'>=</span> "
                f"<span style='color:{val_col}'>{start}</span> "
                f"<span style='color:{hl}'>to </span> "
                f"<span style='color:{val_col}'>{stop}</span> "
                f"<span style='color:{hl}'>with </span> "
                f"<span style='color:{val_col}'>{step}</span> "
                f"<span style='color:{hl}'>spacing:</span>"
            )
        case LinspaceLoop(variable, start, stop, num, sub_steps):
            return (
                f"<span style='color:{hl}'>for</span> "
                f"<span style='color:{var_col}'>{variable}</span> "
                "<span style='color:#FFFFFF'>=</span> "
                f"<span style='color:{val_col}'>{start}</span> "
                f"<span style='color:{hl}'>to </span> "
                f"<span style='color:{val_col}'>{stop}</span> "
                f"<span style='color:{hl}'>with </span> "
                f"<span style='color:{val_col}'>{num}</span> "
                f"<span style='color:{hl}'>steps:</span>"
            )
        case ImportConstantTable(table, alias):
            if alias is None:
                return (
                    f"<span style='color:{hl}'>import</span> "
                    f"<span style='color:{text_col}'>{table}</span>"
                )
            else:
                return (
                    f"<span style='color:{hl}'>import</span> "
                    f"<span style='color:{text_col}'> {table}</span> "
                    f"<span style='color:{hl}'>as</span> "
                    f"<span style='color:{text_col}'>{alias}</span>"
                )

        case _:
            assert_never(step)


class StepDelegate(QStyledItemDelegate):
    def __init__(self, parent: Optional[QWidget] = None):
        self.doc = QTextDocument()
        super().__init__(parent)

    def paint(self, painter, option, index):
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        painter.save()
        self.doc.setTextWidth(options.rect.width())
        text = to_str(index.data(role=Qt.ItemDataRole.DisplayRole))
        self.doc.setHtml(text)
        self.doc.setDefaultFont(options.font)
        options.text = ""
        options.widget.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_ItemViewItem, options, painter
        )
        painter.translate(options.rect.left(), options.rect.top())
        clip = QRectF(0, 0, options.rect.width(), options.rect.height())
        painter.setClipRect(clip)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.clip = clip
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        self.doc.setHtml(option.text)
        self.doc.setTextWidth(option.rect.width())
        return QtCore.QSize(int(self.doc.idealWidth()), int(self.doc.size().height()))

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget:
        editor = QLineEdit()
        editor.setParent(parent)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        match data:
            case VariableDeclaration(variable, value):
                text = f"{variable} = {value}"
                editor.setValidator(VariableDeclarationValidator())
                editor.setText(text)
            case LinspaceLoop(variable, start, stop, num, sub_steps):
                text = f"for {variable} = {start} to {stop} with {num} steps:"
                editor.setValidator(LinSpaceLoopValidator())
                editor.setText(text)
            case ArangeLoop(variable, start, stop, step, sub_steps):
                text = f"for {variable} = {start} to {stop} with {step} spacing:"
                editor.setValidator(ArangeLoopValidator())
                editor.setText(text)
            case ImportConstantTable(table, alias):
                if alias is None:
                    text = f"import {table}"
                else:
                    text = f"import {table} as {alias}"
                editor.setValidator(ImportConstantTableValidator())
                editor.setText(text)
            case _:
                raise ValueError(f"Can't set editor data for {data}")

    def updateEditorGeometry(
        self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):
        geometry = option.rect
        editor.setGeometry(geometry)

    def setModelData(
        self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex
    ) -> None:
        editor: QLineEdit
        previous_data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        text = editor.text()
        match previous_data:
            case ImportConstantTable():
                match = IMPORT_CONSTANT_TABLE_REGEX.fullmatch(text)
                if match:
                    new_attributes = {
                        "table": DottedVariableName(match.group("table")),
                        "alias": DottedVariableName(match.group("alias"))
                        if match.group("alias")
                        else None,
                    }
                    model.setData(index, new_attributes, Qt.ItemDataRole.EditRole)
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


class ImportConstantTableValidator(QValidator):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def validate(self, input: str, pos: int) -> tuple[QValidator.State, str, int]:
        if IMPORT_CONSTANT_TABLE_REGEX.fullmatch(input):
            return QValidator.State.Acceptable, input, pos
        else:
            return QValidator.State.Invalid, input, pos


class VariableDeclarationEditor(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout()
        self.variable = AutoResizeLineEdit(self)
        self.value = AutoResizeLineEdit(self)
        layout.addWidget(self.variable)
        label = QtWidgets.QLabel(self)
        label.setText("=")
        label.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0)
        layout.addWidget(self.value, 0)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_data(self, data: VariableDeclaration):
        self.variable.setText(str(data.variable))
        self.value.setText(str(data.value))

    def get_data(self) -> VariableDeclaration:
        return VariableDeclaration(
            variable=DottedVariableName(self.variable.text()),
            value=Expression(self.value.text()),
        )
