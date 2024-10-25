from typing import Optional, override

import attrs
from PySide6.QtWidgets import QWidget, QFormLayout

from ._editor_builder import EditorBuilder
from .._value_editor import ValueEditor


def build_editor_for_attrs_class[
    T: attrs.AttrsInstance
](cls: type[T], builder: EditorBuilder) -> type[ValueEditor[T]]:
    fields: tuple[attrs.Attribute] = attrs.fields(cls)
    attribute_editors = {}
    for field in fields:
        if field.type is None:
            raise ValueError(
                f"No type specified for field {field.name} for class {cls}"
            )
        attribute_editors[field.name] = builder.build_editor(field.type)

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
