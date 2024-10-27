import inspect
from typing import override

import attrs
import docstring_parser
from PySide6.QtWidgets import QWidget, QFormLayout, QLabel

from ._editor_builder import EditorBuilder, EditorBuildingError, EditorFactory
from .._value_editor import ValueEditor


def build_attrs_class_editor[
    T: attrs.AttrsInstance
](cls: type[T], builder: EditorBuilder, **attr_editors: EditorFactory) -> EditorFactory[
    T
]:
    """Build an editor for attrs class.

    This function will build a form editor with a list of widgets for the attributes of
    the class.

    The label for each widget is the name of the attribute, prettified by removing
    underscores and capitalizing the first letter of the first word.

    The tooltip of this label is the docstring of the attribute.

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

    attribute_docstrings = extract_attribute_docstrings(cls)

    attribute_editors = {}
    for field in fields:
        if field.name in attr_editors:
            attribute_editors[field.name] = attr_editors[field.name]
            continue
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
        def __init__(self, value: T) -> None:
            self._widget = QWidget()

            layout = QFormLayout()
            self._widget.setLayout(layout)
            for field in fields:
                editor = attribute_editors[field.name](getattr(value, field.name, None))
                setattr(self, attr_to_editor_name(field.name), editor)
                label = QLabel(prettify_snake_case(field.name))
                if field.name in attribute_docstrings:
                    label.setToolTip(attribute_docstrings[field.name])
                layout.addRow(label, editor.widget())

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


def extract_attribute_docstrings(cls: type) -> dict[str, str]:
    """Extract docstrings of attributes from a class.

    Args:
        cls: The class to extract the docstrings from.

    Returns:
        A dictionary mapping attribute names to their docstrings.

        Not all attributes may have docstrings, so the dictionary may not contain all
        attributes, or may be empty.
    """

    docstring = inspect.getdoc(cls)

    if docstring:
        parsed = docstring_parser.parse(docstring)
        return {
            param.arg_name: param.description
            for param in parsed.params
            if param.description is not None
        }
    else:
        return {}


class AttributeEditorBuildingError(EditorBuildingError):
    def __init__(self, cls: type[attrs.AttrsInstance], attribute: attrs.Attribute):
        msg = f"Could not build editor for attribute '{attribute.name}' of {cls}"
        super().__init__(msg)
