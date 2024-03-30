import copy
from collections.abc import Mapping, Iterable, Callable
from typing import TypedDict, Optional, TypeVar, Generic

from PySide6.QtCore import QStringListModel, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QColumnView,
    QVBoxLayout,
    QDialogButtonBox,
)

from caqtus.device import DeviceConfigurationAttrs, DeviceName
from .add_device_dialog_ui import Ui_AddDeviceDialog
from .device_configuration_editor import (
    DeviceConfigurationEditor,
    DefaultDeviceConfigurationEditor,
)
from .device_configurations_dialog_ui import Ui_DeviceConfigurationsDialog
from ..icons import get_icon

T = TypeVar("T", bound=DeviceConfigurationAttrs)


class DeviceConfigurationEditInfo(TypedDict, Generic[T]):
    editor_type: type[DeviceConfigurationEditor[T]]


C = TypeVar("C", bound=DeviceConfigurationAttrs)

DeviceConfigurationEditorFactory = Callable[[C], DeviceConfigurationEditor[C]]


def default_device_editor_factory(
    device_configuration: C,
) -> DeviceConfigurationEditor[C]:
    return DefaultDeviceConfigurationEditor(device_configuration)


class DeviceConfigurationsView(QColumnView):
    """View for displaying a collection of device configurations."""

    def __init__(
        self,
        device_editor_factory: DeviceConfigurationEditorFactory,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the view.

        Args:
            device_editor_factory: A factory function that creates an editor for a
            device configuration.
            When the configuration of a device is selected, the view will call this
            function with the configuration as an argument to create an editor for it.
            When the view needs to read the configuration from the editor, it will call
            the method :meth:get_configuration` of the editor.
            Configuration passed to and read from the editor are copies of what is
            stored in the view, so changes to the configuration in the editor will not
            affect the view until the view reads the configuration from the editor.
            parent: The parent widget.
        """

        super().__init__(parent)

        self._device_configurations = []
        self._device_editor_factory = device_editor_factory

        self._model = QStringListModel(self)
        self._sorted_model = QSortFilterProxyModel(self)
        self._sorted_model.setSourceModel(self._model)
        self._sorted_model.sort(0)
        self.setModel(self._sorted_model)
        self.updatePreviewWidget.connect(self._update_preview_widget)
        self._previous_index: Optional[int] = None

    def set_device_configurations(
        self, device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs]
    ) -> None:
        """Set the device configurations to display.

        The view will copy the configurations and store them internally, so external
        changes to the configurations will not affect the view.
        """

        device_configurations = copy.deepcopy(dict(device_configurations))

        self._device_configurations = list(device_configurations.values())
        self._model.setStringList(list(device_configurations.keys()))

    def get_device_configurations(self) -> dict[DeviceName, DeviceConfigurationAttrs]:
        """Return a copy of the configurations currently displayed in the view."""

        # We first need to read the changes from the currently displayed editor before
        # returning the configurations.
        if self._previous_index is not None:
            config_editor = self.previewWidget()
            assert isinstance(config_editor, DeviceConfigurationEditor)
            previous_config = copy.deepcopy(config_editor.get_configuration())
            self._device_configurations[self._previous_index] = previous_config
        return {
            device_name: device_configuration
            for device_name, device_configuration in zip(
                self._model.stringList(), self._device_configurations
            )
        }

    def add_configuration(
        self, device_name: DeviceName, device_configuration: DeviceConfigurationAttrs
    ) -> None:
        """Add a device configuration to the view.

        The view will copy the configuration and store it internally, so external
        changes to the configuration will not affect the view.
        """

        if not isinstance(device_configuration, DeviceConfigurationAttrs):
            raise TypeError(
                f"Expected a DeviceConfigurationAttrs, got {type(device_configuration)}"
            )

        device_configuration = copy.deepcopy(device_configuration)

        self._device_configurations.append(device_configuration)
        self._model.setStringList(self._model.stringList() + [device_name])

    def delete_selected_configuration(self) -> None:
        """Delete the configuration that is currently selected in the view."""

        index = self.currentIndex()
        if index.isValid():
            self._model.removeRow(index.row())
            self._device_configurations.pop(index.row())
            self._previous_index = None

    def _update_preview_widget(self, index) -> None:
        if self._previous_index is not None:
            previous_editor = self.previewWidget()
            assert isinstance(previous_editor, DeviceConfigurationEditor)
            previous_config = copy.deepcopy(previous_editor.get_configuration())
            self._device_configurations[self._previous_index] = previous_config
            previous_editor.deleteLater()
        self._previous_index = index.row()
        new_config = copy.deepcopy(self._device_configurations[index.row()])
        new_editor = self._device_editor_factory(new_config)
        if not isinstance(new_editor, DeviceConfigurationEditor):
            raise TypeError(
                f"Expected a DeviceConfigurationEditor, got {type(new_editor)}"
            )
        previous_editor = new_editor
        self.setPreviewWidget(previous_editor)


DeviceConfigurationFactory = Callable[[], DeviceConfigurationAttrs]


class DeviceConfigurationsDialog(QDialog, Ui_DeviceConfigurationsDialog):
    """A dialog for displaying and editing a collection of device configurations."""

    def __init__(
        self,
        device_editor_factory: DeviceConfigurationEditorFactory,
        device_configuration_factories: Mapping[str, DeviceConfigurationFactory],
        parent: Optional[QWidget] = None,
    ):
        """Initialize the dialog.

        Args:
            device_editor_factory: A factory function that creates an editor for a
            device configuration.
            See :class:`DeviceConfigurationsView` for more information.
            device_configuration_factories: A mapping from device types to factory
            functions that create device configurations of that type.
            When the user adds a new device configuration, the dialog will present a
            list of device types to choose from.
            When the user selects a device type, the dialog will call the factory
            function for that type to create a new device configuration.
            parent: The parent widget.
        """

        super().__init__(parent)
        self._configs_view = DeviceConfigurationsView(device_editor_factory, self)

        self.add_device_dialog = AddDeviceDialog(
            device_configuration_factories.keys(), self
        )
        self.device_configuration_factories = device_configuration_factories

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        self.setupUi(self)
        layout = self.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.insertWidget(0, self._configs_view, 1)
        self.add_device_button.setIcon(get_icon("plus"))
        self.remove_device_button.setIcon(get_icon("minus"))

    def setup_connections(self):
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.add_device_button.clicked.connect(self._on_add_configuration)
        self.remove_device_button.clicked.connect(
            self._configs_view.delete_selected_configuration
        )

    def _on_add_configuration(self) -> None:
        result = self.add_device_dialog.exec()
        if result is not None:
            device_name, device_type = result
            if not device_name:
                return
            device_configuration = self.device_configuration_factories[device_type]()
            self._configs_view.add_configuration(device_name, device_configuration)

    def get_device_configurations(self) -> dict[DeviceName, DeviceConfigurationAttrs]:
        return self._configs_view.get_device_configurations()


class AddDeviceDialog(QDialog, Ui_AddDeviceDialog):
    def __init__(self, device_types: Iterable[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui(device_types)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.device_type_combo_box.currentTextChanged.connect(
            self._on_device_type_changed
        )
        self._on_device_type_changed(self.device_type_combo_box.currentText())

    def _on_device_type_changed(self, device_type: str):
        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        assert ok_button is not None
        ok_button.setEnabled(bool(device_type))

    def setup_ui(self, device_types: Iterable[str]):
        self.setupUi(self)
        for device_type in device_types:
            self.device_type_combo_box.addItem(device_type)

    def exec(self) -> Optional[tuple[DeviceName, str]]:
        result = super().exec()
        if result == QDialog.DialogCode.Accepted:
            if not self.device_name_line_edit.hasAcceptableInput():
                return None
            device_name = self.device_name_line_edit.text()
            device_type = self.device_type_combo_box.currentText()
            return device_name, device_type
        return None
