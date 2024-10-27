from typing import Optional, override

import attrs
from PySide6.QtWidgets import QWidget, QFormLayout

from ._editor_builder import EditorBuilder, EditorBuildingError
from .._value_editor import ValueEditor


def build_editor_for_attrs_class[
    T: attrs.AttrsInstance
](cls: type[T], builder: EditorBuilder, **attr_editors: type[ValueEditor]) -> type[
    ValueEditor[T]
]:
    """Build an editor for attrs class.

    Args:
        cls: The attrs class to build the editor for.
        builder: The editor builder used to build editors for the class attributes.
        **attr_editors: If a named argument corresponds to one of the attributes,
            the editor passed for this argument will be used instead of using the
            builder.
    """

    fields: tuple[attrs.Attribute] = attrs.fields(cls)

    if any(isinstance(field.type, str) for field in fields):
        # PEP 563 annotations - need to be resolved.
        attrs.resolve_types(cls)

    attribute_editors = {}
    for field in fields:
        if field.name in attr_editors:
            attribute_editors[field.name] = attr_editors[field.name]
        if field.type is None:
            raise AttributeEditorBuildingError(cls, field) from ValueError(
                "No type specified"
            )
        try:
            attribute_editors[field.name] = builder.build_editor(field.type)
        except EditorBuildingError as e:
            raise AttributeEditorBuildingError(cls, field) from e

    class AttrsEditor(ValueEditor[T]):
        @override
        def __init__(self, value: T, parent: Optional[QWidget] = None) -> None:
            self._widget = QWidget(parent)

            layout = QFormLayout()
            self._widget.setLayout(layout)
            for field in fields:
                editor = attribute_editors[field.name](getattr(value, field.name, None))
                setattr(self, attr_to_editor_name(field.name), editor)
                layout.addRow(prettify_snake_case(field.name), editor.widget())

        # TODO: Figure out why pyright report this method as an incompatible override
        @override
        def read_value(self) -> T:  # type: ignore[reportIncompatibleMethodOverride]
            attribute_values = {}
            for field in fields:
                editor = getattr(self, attr_to_editor_name(field.name))
                assert isinstance(editor, ValueEditor)
                attribute_values[field.name] = editor.read_value()
            return cls(**attribute_values)

        @override
        def set_editable(self, editable: bool) -> None:
            for field in fields:
                editor = getattr(self, attr_to_editor_name(field.name))
                assert isinstance(editor, ValueEditor)
                editor.set_editable(editable)

        @override
        def widget(self) -> QWidget:
            return self._widget

    return AttrsEditor


def prettify_snake_case(name: str) -> str:
    if name:
        words = name.split("_")
        words[0] = words[0].title()
        return " ".join(words)
    else:
        return name


def attr_to_editor_name(name: str) -> str:
    return f"editor_{name}"


class AttributeEditorBuildingError(EditorBuildingError):
    def __init__(self, cls: type[attrs.AttrsInstance], attribute: attrs.Attribute):
        msg = f"Could not build editor for attribute '{attribute.name}' of {cls}"
        super().__init__(msg)
