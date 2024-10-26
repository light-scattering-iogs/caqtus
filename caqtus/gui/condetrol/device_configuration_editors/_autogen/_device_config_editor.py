from typing import Optional

from PySide6.QtWidgets import QWidget, QLayout

from caqtus.device import DeviceConfiguration
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from ._editor_builder import EditorBuilder


def build_device_configuration_editor[
    C: DeviceConfiguration
](config_type: type[C], builder: EditorBuilder) -> type[DeviceConfigurationEditor[C]]:
    """Builds a device configuration editor for the given configuration type.

    Args:
        config_type: The type of configuration to construct the editor for.
        builder: Used to build editors for the fields of the configuration.

    Returns:
        An automatically generated class of type :class:`DeviceConfigurationEditor`
        that can be used to edit configurations with type `config_type`.
    """

    config_editor_type = builder.build_editor_for_type(config_type)

    class GeneratedConfigEditor(DeviceConfigurationEditor[C]):
        def __init__(self, config: C, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self.editor = config_editor_type(config, self)
            layout = QLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.editor.widget())
            self.setLayout(layout)

        # TODO: Understand why need to silence pyright
        def get_configuration(self) -> C:  # type: ignore[reportIncompatibleMethodOverride]
            return self.editor.read_value()

    return GeneratedConfigEditor
