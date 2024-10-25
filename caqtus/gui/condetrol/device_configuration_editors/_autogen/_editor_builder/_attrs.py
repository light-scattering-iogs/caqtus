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
            self._editors = {
                field.name: attribute_editors[field.name](
                    getattr(value, field.name), None
                )
                for field in fields
            }
            layout = QFormLayout()
            self._widget.setLayout(layout)
            for label, editor in self._editors.items():
                layout.addRow(prettify_snake_case(label), editor.widget())

        # TODO: Figure out why pyright report this method as an incompatible override
        @override
        def get_value(self) -> T:  # type: ignore[reportIncompatibleMethodOverride]
            attribute_values = {
                name: editor.get_value() for name, editor in self._editors.items()
            }
            return cls(**attribute_values)

        @override
        def set_editable(self, editable: bool) -> None:
            for editor in self._editors.values():
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
