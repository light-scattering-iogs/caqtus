from typing import Optional

from PySide6.QtCore import (
    QObject,
    Qt,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget, QColumnView, QSizePolicy

from core.session import ParameterNamespace, is_parameter_namespace
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from .parameter_tables_editor_ui import Ui_ParameterTablesEditor
from ..icons import get_icon

PARAMETER_NAME_ROLE = Qt.UserRole + 1
PARAMETER_VALUE_ROLE = Qt.UserRole + 2


class ParameterTablesEditor(QWidget, Ui_ParameterTablesEditor):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.view = ColumnView(self)
        self.view.setResizeGripsVisible(True)
        self._model = ParameterNamespaceModel(self)
        self.view.setModel(self._model)

        self.setup_ui()
        self.set_read_only(False)

    def setup_ui(self):
        self.setupUi(self)
        self._layout.insertWidget(0, self.view)
        self.set_parameters({})

    def set_read_only(self, read_only: bool) -> None:
        if read_only:
            self.on_set_to_read_only()
        else:
            self.on_set_to_editable()

    def on_set_to_read_only(self) -> None:
        self.add_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.paste_from_clipboard_button.setEnabled(False)

    def on_set_to_editable(self) -> None:
        self.add_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.paste_from_clipboard_button.setEnabled(True)

    def set_parameters(self, parameters: ParameterNamespace) -> None:
        """Set the parameters to be displayed in the table.

        This method ignore the read-only flag and always set the parameters displayed.
        """

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


class ColumnView(QColumnView):
    """A QColumnView that does not show a preview widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fix to hide the preview widget column
        # see: https://bugreports.qt.io/browse/QTBUG-1826
        self.w = QWidget()
        self.w.setMaximumSize(0, 0)
        self.w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setPreviewWidget(self.w)
        self.updatePreviewWidget.connect(self._on_update_preview_widget)

    def _on_update_preview_widget(self, index):
        self.w.parentWidget().parentWidget().setMinimumWidth(0)
        self.w.parentWidget().parentWidget().setMaximumWidth(0)


class ParameterNamespaceModel(QStandardItemModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def set_parameters(self, parameters: ParameterNamespace) -> None:
        root = self.invisibleRootItem()
        root.removeRows(0, root.rowCount())
        for name, value in parameters.items():
            item = self._create_item(name, value)
            root.appendRow(item)

    def get_parameters(self) -> ParameterNamespace:
        namespace = {}
        root = self.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            name, value = self._get_parameters_from_item(item)
            namespace[name] = value
        return namespace

    def _get_parameters_from_item(
        self, item: QStandardItem
    ) -> tuple[DottedVariableName, ParameterNamespace | Expression]:
        name = item.data(PARAMETER_NAME_ROLE)
        assert isinstance(name, DottedVariableName)
        value = item.data(PARAMETER_VALUE_ROLE)
        assert isinstance(value, Expression) or value is None
        if value is None:
            result = {}
            for row in range(item.rowCount()):
                sub_item = item.child(row)
                sub_name, sub_value = self._get_parameters_from_item(sub_item)
                result[sub_name] = sub_value
        else:
            result = value
        return name, result

    def _create_item(
        self, name: DottedVariableName, value: ParameterNamespace | Expression
    ) -> QStandardItem:
        item = QStandardItem()
        if isinstance(value, Expression):
            item.setData(f"{name} = {value}", Qt.ItemDataRole.DisplayRole)
            item.setData(name, PARAMETER_NAME_ROLE)
            item.setData(value, PARAMETER_VALUE_ROLE)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemNeverHasChildren
            )
        elif is_parameter_namespace(value):
            item.setData(str(name), Qt.ItemDataRole.DisplayRole)
            item.setData(name, PARAMETER_NAME_ROLE)
            item.setData(None, PARAMETER_VALUE_ROLE)
            for sub_name, sub_value in value.items():
                sub_item = self._create_item(sub_name, sub_value)
                item.appendRow(sub_item)
            item.setData(None, Qt.ItemDataRole.UserRole)
        else:
            raise ValueError(f"Invalid value {value}")
        return item
