import copy
from collections.abc import Mapping, Iterable, Callable
from typing import TypedDict, Optional, TypeVar, Generic

from PySide6.QtCore import QStringListModel, QSortFilterProxyModel
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDialog, QWidget, QColumnView

from caqtus.device import DeviceConfigurationAttrs, DeviceName
from .add_device_dialog_ui import Ui_AddDeviceDialog
from .configurations_editor_ui import Ui_ConfigurationsEditor
from .device_configuration_editor import (
    DeviceConfigurationEditor,
    DefaultDeviceConfigurationEditor,
)
from ..save_geometry_dialog import SaveGeometryDialog

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


class ConfigurationsEditor(SaveGeometryDialog, Ui_ConfigurationsEditor):
    def __init__(
        self,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
        device_configuration_edit_info: Mapping[str, DeviceConfigurationEditInfo],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.device_configurations = device_configurations
        self.device_configuration_edit_info = device_configuration_edit_info

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        self.setupUi(self)
        self.tab_widget.clear()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.tab_widget.removeTab)
        self.tab_widget.setMovable(True)
        for device_name, device_configuration in self.device_configurations.items():
            type_name = type(device_configuration).__qualname__
            if type_name not in self.device_configuration_edit_info:
                device_configuration_editor = DefaultDeviceConfigurationEditor()
            else:
                device_configuration_editor = self.device_configuration_edit_info[
                    type_name
                ]["editor_type"]()
            self.tab_widget.addTab(device_configuration_editor, device_name)
            device_configuration_editor.set_configuration(device_configuration)

    def setup_connections(self):
        # noinspection PyUnresolvedReferences
        self.add_device_button.clicked.connect(self.add_configuration)

    def add_configuration(self):
        validator = NewNameValidator(
            self.tab_widget.tabText(i) for i in range(self.tab_widget.count())
        )
        add_device_dialog = AddDeviceDialog(
            self.device_configuration_edit_info.keys(),
            validator,
        )
        result = add_device_dialog.exec()
        if result is not None:
            device_name, device_type = result
            device_configuration_editor = self.device_configuration_edit_info[
                device_type
            ]["editor_type"]()
            self.tab_widget.addTab(device_configuration_editor, device_name)

    def exec(self):
        result = super().exec()
        if result == QDialog.DialogCode.Accepted:
            device_configurations = {}
            for i in range(self.tab_widget.count()):
                device_configuration_editor = self.tab_widget.widget(i)
                device_configuration = device_configuration_editor.get_configuration()
                device_configurations[self.tab_widget.tabText(i)] = device_configuration
            self.device_configurations = device_configurations
        return result


class AddDeviceDialog(QDialog, Ui_AddDeviceDialog):
    def __init__(
        self, device_types: Iterable[str], validator: QValidator, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.setup_ui(device_types)
        self.device_name_line_edit.setValidator(validator)

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


class NewNameValidator(QValidator):
    def __init__(self, already_used_names: Iterable[str]):
        super().__init__()
        self.already_used_names = set(already_used_names)

    def validate(self, a0, a1):
        if a0 in self.already_used_names or a0 == "":
            return QValidator.State.Intermediate, a0, a1
        else:
            return QValidator.State.Acceptable, a0, a1
