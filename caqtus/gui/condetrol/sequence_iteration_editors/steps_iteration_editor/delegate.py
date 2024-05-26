from typing import Optional, assert_never

from PySide6.QtCore import QModelIndex, Qt, QAbstractItemModel, QObject, QEvent
from PySide6.QtGui import (
    QTextDocument,
    QPalette,
    QFocusEvent,
)
from PySide6.QtWidgets import (
    QLineEdit,
    QWidget,
    QStyleOptionViewItem,
    QHBoxLayout,
    QLabel,
    QApplication,
    QSpinBox,
)

from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    Step,
    VariableDeclaration,
    LinspaceLoop,
    ArangeLoop,
    ExecuteShot,
)
from caqtus.types.variable_name import (
    DottedVariableName,
    InvalidVariableNameError,
)
from ...qt_util import AutoResizeLineEdit, HTMLItemDelegate

NAME_COLOR = "#AA4926"
VALUE_COLOR = "#6897BB"
HIGHLIGHT_COLOR = "#cc7832"


def to_str(step: Step) -> str:
    hl = HIGHLIGHT_COLOR
    text_color = f"#{QPalette().text().color().rgba():X}"
    var_col = NAME_COLOR
    val_col = VALUE_COLOR
    match step:
        case ExecuteShot():
            return f"<span style='color:{hl}'>do shot</span>"
        case VariableDeclaration(variable, value):
            return (
                f"<span style='color:{var_col}'>{variable}</span> "
                f"<span style='color:{text_color}'>=</span> "
                f"<span style='color:{val_col}'>{value}</span>"
            )
        case ArangeLoop(variable, start, stop, step, sub_steps):
            return (
                f"<span style='color:{hl}'>for</span> "
                f"<span style='color:{var_col}'>{variable}</span> "
                f"<span style='color:{text_color}'>=</span> "
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
                f"<span style='color:{text_color}'>=</span> "
                f"<span style='color:{val_col}'>{start}</span> "
                f"<span style='color:{hl}'>to </span> "
                f"<span style='color:{val_col}'>{stop}</span> "
                f"<span style='color:{hl}'>with </span> "
                f"<span style='color:{val_col}'>{num}</span> "
                f"<span style='color:{hl}'>steps:</span>"
            )
        case _:
            assert_never(step)


class StepDelegate(HTMLItemDelegate):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.doc = QTextDocument(self)

    def get_text_to_render(self, index: QModelIndex) -> str:
        step: Step = index.data(role=Qt.DisplayRole)
        return to_str(step)

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget:
        value = index.data(role=Qt.DisplayRole)
        if isinstance(value, VariableDeclaration):
            return VariableDeclarationEditor(parent, option.font)
        elif isinstance(value, LinspaceLoop):
            return LinspaceLoopEditor(parent, option.font)
        elif isinstance(value, ArangeLoop):
            return ArrangeLoopEditor(parent, option.font)
        else:
            assert_never(value)

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        data: Step = index.data(role=Qt.ItemDataRole.EditRole)
        match data:
            case VariableDeclaration() as declaration:
                assert isinstance(editor, VariableDeclarationEditor)
                editor.set_value(declaration)
            case LinspaceLoop() as loop:
                assert isinstance(editor, LinspaceLoopEditor)
                editor.set_value(loop)
            case ArangeLoop():
                assert isinstance(editor, ArrangeLoopEditor)
                editor.set_value(data)
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

        match previous_data:
            case VariableDeclaration():
                assert isinstance(editor, VariableDeclarationEditor)
                try:
                    new_declaration = editor.get_value()
                except InvalidVariableNameError:
                    return
                else:
                    new_attributes = {
                        "variable": new_declaration.variable,
                        "value": new_declaration.value,
                    }
                    model.setData(index, new_attributes, Qt.ItemDataRole.EditRole)
            case LinspaceLoop():
                assert isinstance(editor, LinspaceLoopEditor)
                try:
                    new_values = editor.get_values()
                except InvalidVariableNameError:
                    return
                else:
                    model.setData(index, new_values, Qt.ItemDataRole.EditRole)
            case ArangeLoop():
                assert isinstance(editor, ArrangeLoopEditor)
                try:
                    new_attributes = editor.get_values()
                except InvalidVariableNameError:
                    return
                else:
                    model.setData(index, new_attributes, Qt.ItemDataRole.EditRole)
            case _:
                assert_never(previous_data)


class CompoundWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self._widgets = []

    def add_widget(self, widget: QWidget):
        self.layout().addWidget(widget)
        widget.installEventFilter(self)
        self._widgets.append(widget)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        watched_is_child = watched in self._widgets
        if watched_is_child and event.type() == QEvent.Type.FocusOut:
            if QApplication.focusWidget() not in self.findChildren(QWidget):
                QApplication.postEvent(self, QFocusEvent(event.type()))
            return False

        return super().eventFilter(watched, event)


class LinspaceLoopEditor(CompoundWidget):
    def __init__(self, parent, font):
        super().__init__(parent)
        self.setFont(font)
        for_label = QLabel("for ", self)
        for_label.setAttribute(Qt.WA_TranslucentBackground, True)
        for_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(for_label)
        self.name_editor = AutoResizeLineEdit(self)
        self.name_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.name_editor)
        equal_label = QLabel("=", self)
        equal_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.add_widget(equal_label)
        self.start_editor = AutoResizeLineEdit(self)
        self.start_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.start_editor)
        to_label = QLabel(" to ", self)
        to_label.setAttribute(Qt.WA_TranslucentBackground, True)
        to_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(to_label)
        self.stop_editor = AutoResizeLineEdit(self)
        self.start_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.stop_editor)
        with_label = QLabel(" with ", self)
        with_label.setAttribute(Qt.WA_TranslucentBackground, True)
        with_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(with_label)
        self.num_editor = QSpinBox(self)
        self.num_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.num_editor.setRange(0, 9999)
        self.add_widget(self.num_editor)
        steps_label = QLabel(" steps:", self)
        steps_label.setAttribute(Qt.WA_TranslucentBackground, True)
        steps_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(steps_label)
        self.layout().addStretch(1)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def set_value(self, loop: LinspaceLoop) -> None:
        self.name_editor.setText(str(loop.variable))
        self.start_editor.setText(str(loop.start))
        self.stop_editor.setText(str(loop.stop))
        self.num_editor.setValue(loop.num)

    def get_values(self) -> dict:
        return {
            "variable": DottedVariableName(self.name_editor.text()),
            "start": Expression(self.start_editor.text()),
            "stop": Expression(self.stop_editor.text()),
            "num": self.num_editor.value(),
        }


class VariableDeclarationEditor(CompoundWidget):
    def __init__(self, parent, font):
        super().__init__(parent)
        self.setFont(font)
        self.name_editor = AutoResizeLineEdit(self)
        self.add_widget(self.name_editor)
        label = QLabel("=", self)
        label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.add_widget(label)
        self.value_editor = AutoResizeLineEdit(self)
        self.add_widget(self.value_editor)
        self.layout().addStretch(1)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.name_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.value_editor.setStyleSheet(f"color: {VALUE_COLOR}")
        self.name_editor.setPlaceholderText("Parameter name")
        self.value_editor.setPlaceholderText("Parameter value")

    def set_value(self, declaration: VariableDeclaration) -> None:
        self.name_editor.setText(str(declaration.variable))
        self.value_editor.setText(str(declaration.value))

    def get_value(self) -> VariableDeclaration:
        name = DottedVariableName(self.name_editor.text())
        value = Expression(self.value_editor.text())
        return VariableDeclaration(variable=name, value=value)


class ArrangeLoopEditor(CompoundWidget):
    def __init__(self, parent, font):
        super().__init__(parent)
        self.setFont(font)
        for_label = QLabel("for ", self)
        for_label.setAttribute(Qt.WA_TranslucentBackground, True)
        for_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(for_label)
        self.name_editor = AutoResizeLineEdit(self)
        self.name_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.name_editor)
        equal_label = QLabel("=", self)
        equal_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.add_widget(equal_label)
        self.start_editor = AutoResizeLineEdit(self)
        self.start_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.start_editor)
        to_label = QLabel(" to ", self)
        to_label.setAttribute(Qt.WA_TranslucentBackground, True)
        to_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(to_label)
        self.stop_editor = AutoResizeLineEdit(self)
        self.start_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.stop_editor)
        with_label = QLabel(" with ", self)
        with_label.setAttribute(Qt.WA_TranslucentBackground, True)
        with_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(with_label)
        self.step_editor = AutoResizeLineEdit(self)
        self.step_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.add_widget(self.step_editor)
        spacing_label = QLabel(" spacing:", self)
        spacing_label.setAttribute(Qt.WA_TranslucentBackground, True)
        spacing_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}")
        self.add_widget(spacing_label)
        self.layout().addStretch(1)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def set_value(self, loop: ArangeLoop) -> None:
        self.name_editor.setText(str(loop.variable))
        self.start_editor.setText(str(loop.start))
        self.stop_editor.setText(str(loop.stop))
        self.step_editor.setText(str(loop.step))

    def get_values(self) -> dict:
        return {
            "variable": DottedVariableName(self.name_editor.text()),
            "start": Expression(self.start_editor.text()),
            "stop": Expression(self.stop_editor.text()),
            "step": Expression(self.step_editor.text()),
        }
