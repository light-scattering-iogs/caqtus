import copy
import functools
from typing import Optional, Protocol

from PySide6.QtWidgets import QLineEdit, QVBoxLayout

from caqtus.device import DeviceConfiguration
from caqtus.device.configuration import DeviceServerName
from caqtus.device.output_transform import EvaluableOutput
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from caqtus.gui.condetrol.device_configuration_editors.camera_configuration_editor import (  # noqa E501
    RectangularROIEditor as RectangularROIWidget,
)
from caqtus.types.expression import Expression
from caqtus.types.image.roi import RectangularROI
from ._editor_builder import EditorBuilder, EditorFactory
from ._expression_editor import ExpressionEditor
from ._output_transform_editor import OutputTransformEditor
from ._value_editor import ValueEditor


class GeneratedConfigEditor[C: DeviceConfiguration](DeviceConfigurationEditor[C]):
    def __init__(
        self,
        config: C,
        *,
        editor_factory: EditorFactory[C],
    ) -> None:
        super().__init__()
        self._editor = editor_factory()
        self._editor.set_value(config)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor.widget())
        self.setLayout(layout)

    # TODO: Understand why need to silence pyright
    def get_configuration(self) -> C:  # type: ignore[reportIncompatibleMethodOverride]
        return self._editor.read_value()

    def set_editable(self, editable: bool) -> None:
        self._editor.set_editable(editable)


class DeviceConfigEditorFactory[C: DeviceConfiguration](Protocol):
    def __call__(self, config: C) -> GeneratedConfigEditor[C]: ...


_builder = EditorBuilder()


def build_device_configuration_editor[
    C: DeviceConfiguration
](
    config_type: type[C],
    builder: EditorBuilder = _builder,
) -> DeviceConfigEditorFactory[C]:
    """Builds a device configuration editor for the given configuration type.

    Args:
        config_type: The type of configuration to construct the editor for.
            If it is an attrs class, the editor build will contain a list of editors
            for each attribute of the class.
        builder: Used to build editors for the fields of the configuration.

    Returns:
        An automatically generated class of type
        :class:`~caqtus.gui.condetrol.device_configuration_editors.DeviceConfigurationEditor`
        that can be used to edit configurations with type `config_type`.
    """

    config_editor_factory = builder.build_editor(config_type)
    return functools.partial(
        GeneratedConfigEditor, editor_factory=config_editor_factory
    )


class DeviceServerNameEditor(ValueEditor[Optional[DeviceServerName]]):
    def __init__(self) -> None:
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("None")

    def set_value(self, value: Optional[DeviceServerName]) -> None:
        if value:
            self.line_edit.setText(value)
        else:
            self.line_edit.setText("")

    def read_value(self) -> Optional[DeviceServerName]:
        text = self.line_edit.text()
        if text:
            return DeviceServerName(text)
        else:
            return None

    def set_editable(self, editable: bool) -> None:
        self.line_edit.setReadOnly(not editable)

    def widget(self) -> QLineEdit:
        return self.line_edit


class RectangularROIEditor(ValueEditor[RectangularROI]):
    def __init__(self) -> None:
        self._widget = RectangularROIWidget(100, 100)

    def set_value(self, value: RectangularROI) -> None:
        self._widget.set_roi(value)

    def read_value(self) -> RectangularROI:
        return self._widget.get_roi()

    def set_editable(self, editable: bool) -> None:
        self._widget.set_editable(editable)

    def widget(self) -> RectangularROIWidget:
        return self._widget


_builder.register_editor(Optional[DeviceServerName], DeviceServerNameEditor)
_builder.register_editor(RectangularROI, RectangularROIEditor)
_builder.register_editor(EvaluableOutput, OutputTransformEditor)
_builder.register_editor(Expression, ExpressionEditor)


def get_editor_builder() -> EditorBuilder:
    """Return a new editor builder with basic types registered.

    The editor builder returned knows how to handle:

        - Device server name
        - :class:`~caqtus.types.image.roi.RectangularROI`
        - :class:`~caqtus.types.expression.Expression`
    """

    return copy.deepcopy(_builder)
