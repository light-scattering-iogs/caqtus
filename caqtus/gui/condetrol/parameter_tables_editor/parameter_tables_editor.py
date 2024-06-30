from collections.abc import Iterable
from typing import Optional

from PySide6.QtCore import (
    QObject,
    Qt,
    Signal,
    QModelIndex,
    QMimeData,
    QEvent,
)
from PySide6.QtGui import (
    QStandardItemModel,
    QStandardItem,
    QPalette,
    QFocusEvent,
    QFont,
)
from PySide6.QtWidgets import (
    QWidget,
    QColumnView,
    QSizePolicy,
    QApplication,
    QToolBar,
    QToolButton,
    QMenu,
    QVBoxLayout,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QStyleOptionViewItem,
)

from caqtus.gui.common.exception_tree import ExceptionDialog
from caqtus.gui.qtutil import block_signals, temporary_widget
from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ..icons import get_icon
from ..logger import logger
from ..qt_util import AutoResizeLineEdit
from ...qtutil import HTMLItemDelegate

logger = logger.getChild("parameters_editor")

PARAMETER_NAME_ROLE = Qt.UserRole + 1
PARAMETER_VALUE_ROLE = Qt.UserRole + 2


class ParameterNamespaceEditor(QWidget):
    """A widget that allows to edit a ParameterNamespace.

    This widget presents a column view with the parameters and namespaces in each
    column.
    It also has a toolbar with buttons to add, remove, copy and paste parameters.
    """

    # The argument is a ParameterNamespace, but this is not a valid type for the
    # Signal.
    parameters_edited = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.view = ParameterNamespaceView(self)

        self.tool_bar = QToolBar(self)

        self._model = ParameterNamespaceModel(self)
        self.view.setModel(self._model)

        self.add_button = QToolButton(self)
        self.add_menu = QMenu(self)
        self.add_parameter_action = self.add_menu.addAction("Add parameter")
        self.add_namespace_action = self.add_menu.addAction("Add namespace")

        self.delete_button = QToolButton(self)
        self.copy_to_clipboard_button = QToolButton(self)
        self.paste_from_clipboard_button = QToolButton(self)

        self.setup_ui()
        self.setup_connections()
        self.set_read_only(False)

        font = QFont("JetBrains Mono")
        self.setFont(font)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addWidget(self.tool_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.copy_to_clipboard_button.clicked.connect(
            self.on_copy_to_clipboard_button_clicked
        )
        self.paste_from_clipboard_button.clicked.connect(
            self.on_paste_from_clipboard_button_clicked
        )
        self.add_button.setMenu(self.add_menu)
        self.add_button.setToolTip("Add")
        self.add_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.delete_button.setToolTip("Remove")
        self.copy_to_clipboard_button.setToolTip("Copy to clipboard")
        self.paste_from_clipboard_button.setToolTip("Paste from clipboard")
        self.tool_bar.addWidget(self.add_button)
        self.tool_bar.addWidget(self.delete_button)
        self.tool_bar.addSeparator()
        self.tool_bar.addWidget(self.copy_to_clipboard_button)
        self.tool_bar.addWidget(self.paste_from_clipboard_button)

        self.set_parameters(ParameterNamespace.empty())

    def setup_connections(self) -> None:
        def emit_edited_signal(*_):
            self.parameters_edited.emit(self.get_parameters())

        self._model.dataChanged.connect(emit_edited_signal)
        self._model.modelReset.connect(emit_edited_signal)
        self._model.rowsInserted.connect(emit_edited_signal)
        self._model.rowsRemoved.connect(emit_edited_signal)
        self._model.rowsMoved.connect(emit_edited_signal)
        self.delete_button.clicked.connect(self.on_delete_button_clicked)
        self.add_parameter_action.triggered.connect(
            lambda: self._model.add_parameter(
                DottedVariableName("new_parameter"), Expression("...")
            )
        )
        self.add_namespace_action.triggered.connect(
            lambda: self._model.add_namespace(DottedVariableName("new_namespace"))
        )

    def set_read_only(self, read_only: bool) -> None:
        if read_only:
            self.on_set_to_read_only()
        else:
            self.on_set_to_editable()

    def on_set_to_read_only(self) -> None:
        self.add_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.paste_from_clipboard_button.setEnabled(False)
        self._model.set_read_only(True)

    def on_set_to_editable(self) -> None:
        self.add_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.paste_from_clipboard_button.setEnabled(True)
        self._model.set_read_only(False)

    def on_delete_button_clicked(self) -> None:
        """Remove the selected item."""

        index = self.view.currentIndex()
        self._model.removeRow(index.row(), index.parent())

    def set_parameters(self, parameters: ParameterNamespace) -> None:
        """Set the parameters to be displayed in the table.

        This method ignore the read-only flag and always set the parameters displayed.
        It does not emit the parameters_edited signal.
        """

        with block_signals(self):
            self._set_parameters(parameters)

    def _set_parameters(self, parameters: ParameterNamespace) -> None:
        # The palette is not set yet in the __init__, so we need to update the icons
        # here, now that it is set to have the right color.
        color = self.palette().buttonText().color()
        self.add_button.setIcon(get_icon("plus", color))
        self.delete_button.setIcon(get_icon("minus", color))
        self.copy_to_clipboard_button.setIcon(get_icon("copy", color))
        self.paste_from_clipboard_button.setIcon(get_icon("paste", color))
        self._model.set_parameters(parameters)

    def get_parameters(self) -> ParameterNamespace:
        """Return the parameters displayed in the table."""

        return self._model.get_parameters()

    def on_copy_to_clipboard_button_clicked(self) -> None:
        """Copy all the displayed parameters to the clipboard."""

        parameters = self.get_parameters()
        serialized = serialization.to_json(parameters, ParameterNamespace)
        clipboard = QApplication.clipboard()
        clipboard.setText(serialized)

    def on_paste_from_clipboard_button_clicked(self) -> None:
        """Paste the parameters from the clipboard and display them in the table."""

        clipboard = QApplication.clipboard()
        serialized = clipboard.text()
        try:
            parameters = serialization.from_json(serialized, ParameterNamespace)
        except Exception as e:
            with temporary_widget(ExceptionDialog(self)) as dialog:
                dialog.set_exception(e)
                dialog.set_message("The clipboard does not contain valid parameters.")
                dialog.exec()
        else:
            self._set_parameters(parameters)


class ParameterNamespaceView(QColumnView):
    """A custom QColumnView used to display the values in a parameter namespace."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fix to hide the preview widget column
        # see: https://bugreports.qt.io/browse/QTBUG-1826
        self.w = QWidget()
        self.w.setMaximumSize(0, 0)
        self.w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setPreviewWidget(self.w)
        self.updatePreviewWidget.connect(self._on_update_preview_widget)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setResizeGripsVisible(True)

        self.delegate = ParameterEditorDelegate(self)
        self.setItemDelegate(self.delegate)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
            | QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.setSelectionMode(QColumnView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QColumnView.SelectionBehavior.SelectItems)

    def _on_update_preview_widget(self, index):
        self.w.parentWidget().parentWidget().setMinimumWidth(0)
        self.w.parentWidget().parentWidget().setMaximumWidth(0)


class ParameterNamespaceModel(QStandardItemModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._read_only = False

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only

    def mimeTypes(self) -> list[str]:
        return ["text/plain"]

    def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
        items = [self.itemFromIndex(index) for index in indexes]
        data = [self._get_parameters_from_item(item) for item in items]
        serialized = serialization.to_json(data)
        mime_data = QMimeData()
        mime_data.setText(serialized)
        return mime_data

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if self._read_only:
            return False
        json_string = data.text()
        try:
            steps = serialization.from_json(
                json_string,
                list[tuple[DottedVariableName, ParameterNamespace | Expression]],
            )
        except ValueError:
            return False

        new_items = [self._create_item(name, value) for name, value in steps]
        if row == -1:
            row = self.rowCount(parent)
        if not (self.flags(parent) & Qt.ItemFlag.ItemIsDropEnabled):
            return False
        parent_item = (
            self.itemFromIndex(parent) if parent.isValid() else self.invisibleRootItem()
        )
        parent_item.insertRows(row, new_items)
        return True

    def canDropMimeData(self, data, action, row, column, parent):
        if self._read_only:
            return False
        return bool(self.flags(parent) & Qt.ItemFlag.ItemIsDropEnabled)

    def set_parameters(self, parameters: ParameterNamespace) -> None:
        self.removeRows(0, self.rowCount(), QModelIndex())
        for name, value in parameters.items():
            item = self._create_item(name, value)
            self.appendRow(item)
        self.modelReset.emit()

    def get_parameters(self) -> ParameterNamespace:
        namespace = []
        root = self.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            name, value = self._get_parameters_from_item(item)
            namespace.append((name, value))
        return ParameterNamespace(namespace)

    def flags(self, index):
        flags = super().flags(index)
        if self._read_only:
            flags &= ~Qt.ItemFlag.ItemIsEditable
            flags &= ~Qt.ItemFlag.ItemIsDropEnabled
            flags &= ~Qt.ItemFlag.ItemIsDragEnabled
        return flags

    def add_parameter(self, name: DottedVariableName, value: Expression) -> None:
        root = self.invisibleRootItem()
        item = self._create_item(name, value)
        root.appendRow(item)

    def add_namespace(self, name: DottedVariableName) -> None:
        root = self.invisibleRootItem()
        item = self._create_item(name, ParameterNamespace.empty())
        root.appendRow(item)

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        # hasChildren is used to know when to display a new column in the ColumnView,
        # so we only return true when the parent is a namespace.
        if not parent.isValid():
            return True
        item = self.itemFromIndex(parent)
        data = item.data(PARAMETER_VALUE_ROLE)
        assert isinstance(data, Expression) or data is None
        return data is None

    def _get_parameters_from_item(
        self, item: QStandardItem
    ) -> tuple[DottedVariableName, ParameterNamespace | Expression]:
        name = item.data(PARAMETER_NAME_ROLE)
        assert isinstance(name, DottedVariableName)
        value = item.data(PARAMETER_VALUE_ROLE)
        assert isinstance(value, Expression) or value is None
        if value is None:
            namespace = []
            for row in range(item.rowCount()):
                sub_item = item.child(row)
                sub_name, sub_value = self._get_parameters_from_item(sub_item)
                namespace.append((sub_name, sub_value))
            return name, ParameterNamespace(namespace)
        else:
            return name, value

    def _create_item(
        self, name: DottedVariableName, value: ParameterNamespace | Expression
    ) -> QStandardItem:
        item = QStandardItem()
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        if isinstance(value, Expression):
            item.setData(name, PARAMETER_NAME_ROLE)
            item.setData(value, PARAMETER_VALUE_ROLE)
            flags |= Qt.ItemFlag.ItemNeverHasChildren
        elif isinstance(value, ParameterNamespace):
            item.setData(name, PARAMETER_NAME_ROLE)
            item.setData(None, PARAMETER_VALUE_ROLE)
            flags |= Qt.ItemFlag.ItemIsDropEnabled
            for sub_name, sub_value in value.items():
                sub_item = self._create_item(sub_name, sub_value)
                item.appendRow(sub_item)
            item.setData(None, Qt.ItemDataRole.UserRole)
        else:
            raise ValueError(f"Invalid value {value}")
        item.setFlags(flags)
        return item

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction


NAME_COLOR = "#AA4926"
VALUE_COLOR = "#6897BB"


class ParameterEditorDelegate(HTMLItemDelegate):
    """A custom delegate to display and edit the parameters in the view."""

    def get_text_to_render(self, index: QModelIndex) -> str:
        text_color = f"#{self.parent().palette().text().color().rgba():X}"
        name = index.data(PARAMETER_NAME_ROLE)
        assert isinstance(name, DottedVariableName)
        value = index.data(PARAMETER_VALUE_ROLE)
        assert isinstance(value, Expression) or value is None

        if value is None:
            return f"<span style='color:{NAME_COLOR}'>{name}</span>"
        else:
            return (
                f"<span style='color:{NAME_COLOR}'>{name}</span> "
                f"<span style='color:{text_color}'>=</span> "
                f"<span style='color:{VALUE_COLOR}'>{value}</span>"
            )

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget:
        name = index.data(PARAMETER_NAME_ROLE)
        assert isinstance(name, DottedVariableName)
        value = index.data(PARAMETER_VALUE_ROLE)
        assert isinstance(value, Expression) or value is None

        if value is None:
            editor = NamespaceEditor(option.font)
        else:
            editor = ParameterEditor(option.font)
        editor.setParent(parent)
        return editor

    def setEditorData(self, editor, index):
        name = index.data(PARAMETER_NAME_ROLE)
        assert isinstance(name, DottedVariableName)
        value = index.data(PARAMETER_VALUE_ROLE)
        assert isinstance(value, Expression) or value is None

        if value is None:
            assert isinstance(editor, NamespaceEditor)
            editor.set_namespace(name)
        else:
            assert isinstance(editor, ParameterEditor)
            editor.set_parameter(name, value)

    def setModelData(self, editor, model, index):
        name = index.data(PARAMETER_NAME_ROLE)
        assert isinstance(name, DottedVariableName)
        value = index.data(PARAMETER_VALUE_ROLE)
        assert isinstance(value, Expression) or value is None

        if value is None:
            assert isinstance(editor, NamespaceEditor)
            new_name = editor.get_namespace()
            model.setData(index, new_name, PARAMETER_NAME_ROLE)
        else:
            assert isinstance(editor, ParameterEditor)
            new_name, new_value = editor.get_parameter()
            model.setData(index, new_name, PARAMETER_NAME_ROLE)
            model.setData(index, new_value, PARAMETER_VALUE_ROLE)


# The editors below have an event filter to remove the focus from them when one of their
# children loses the focus.
# If we don't do this, the editor will keep the focus when the user clicks
# outside of it, and the delegate will not be able to close the editor.
class ParameterEditor(QWidget):
    def __init__(self, font):
        super().__init__()
        self.setFont(font)
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        self.name_editor = AutoResizeLineEdit(self)
        layout.addWidget(self.name_editor)
        label = QLabel("=", self)
        label.setAttribute(Qt.WA_TranslucentBackground, True)
        layout.addWidget(label)
        self.value_editor = AutoResizeLineEdit(self)
        layout.addWidget(self.value_editor)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.name_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.value_editor.setStyleSheet(f"color: {VALUE_COLOR}")
        self.name_editor.setPlaceholderText("Parameter name")
        self.value_editor.setPlaceholderText("Parameter value")
        self.name_editor.installEventFilter(self)
        self.value_editor.installEventFilter(self)

    def set_parameter(self, name: DottedVariableName, value: Expression) -> None:
        self.name_editor.setText(str(name))
        self.value_editor.setText(str(value))

    def get_parameter(self) -> tuple[DottedVariableName, Expression]:
        name = DottedVariableName(self.name_editor.text())
        value = Expression(self.value_editor.text())
        return name, value

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        watched_is_child = watched is self.name_editor or watched is self.value_editor
        if watched_is_child and event.type() == QEvent.Type.FocusOut:
            if QApplication.focusWidget() not in self.findChildren(QWidget):
                QApplication.postEvent(self, QFocusEvent(event.type()))
            return False

        return super().eventFilter(watched, event)


class NamespaceEditor(QWidget):
    def __init__(self, font):
        super().__init__()
        self.setFont(font)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.name_editor = AutoResizeLineEdit(self)
        layout.addWidget(self.name_editor)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.name_editor.setStyleSheet(f"color: {NAME_COLOR}")
        self.name_editor.setPlaceholderText("Namespace name")
        self.name_editor.installEventFilter(self)

    def set_namespace(self, name: DottedVariableName) -> None:
        self.name_editor.setText(str(name))

    def get_namespace(self) -> DottedVariableName:
        name = DottedVariableName(self.name_editor.text())
        return name

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.name_editor and event.type() == QEvent.Type.FocusOut:
            QApplication.postEvent(self, QFocusEvent(event.type()))
            return False

        return super().eventFilter(watched, event)
