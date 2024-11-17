from __future__ import annotations

import functools
import typing
from collections.abc import Sequence

import annotated_types
import attrs
from PySide6.QtWidgets import QWidget, QFormLayout, QLabel

from ._editor_builder import EditorBuilder, EditorBuildingError, EditorFactory, TypeExpr
from .._value_editor import ValueEditor


def build_attrs_class_editor[
    T: attrs.AttrsInstance
](
    cls: type[T], builder: EditorBuilder, **attr_overrides: AttributeOverride
) -> EditorFactory[T]:
    """Build an editor for attrs class.

    This function will build a form editor with a list of widgets for the attributes of
    the class.

    The label for each widget is the name of the attribute, prettified by removing
    underscores and capitalizing the first letter of the first word.

    If an attribute is annotated like this
    `typing.Annotated[T, annotated_types.doc("Some documentation")]`,
    the documentation will be used as a tooltip for the label.

    Args:
        cls: The attrs class to build the editor for.
        builder: The editor builder used to build editors for the class attributes.
        **attr_overrides: If a named argument corresponds to one of the
            attributes, the object passed as argument will override the automated ui
            generation for that attribute.
    """

    fields: tuple[attrs.Attribute, ...] = attrs.fields(cls)

    if any(isinstance(field.type, str) for field in fields):
        # PEP 563 annotations - need to be resolved.
        attrs.resolve_types(cls)

    attr_ui_infos = []
    for field in fields:
        override = attr_overrides.get(field.name, None)
        try:
            label = get_attribute_label(field, override)
            editor_factory = get_attribute_editor_factory(field, override, builder)
            tooltip = get_attribute_tooltip(field, override)
        except Exception as e:
            raise AttributeEditorBuildingError(cls, field) from e
        attr_ui_infos.append(
            AttributeUIInfo(
                field_name=field.name,
                label=label,
                editor_factory=editor_factory,
                tooltip=tooltip,
            )
        )

    return functools.partial(AttrsEditor, cls, tuple(attr_ui_infos))


class AttrsEditor[T: attrs.AttrsInstance](ValueEditor[T]):
    """A generic editor for attrs classes."""

    def __init__(self, cls: type[T], ui_specs: Sequence[AttributeUIInfo]) -> None:
        self._widget = QWidget()
        self._ui_specs = ui_specs
        self._cls = cls

        layout = QFormLayout()
        self._widget.setLayout(layout)
        for ui_spec in ui_specs:
            editor = ui_spec.editor_factory()
            setattr(self, ui_spec.editor_name, editor)
            label = QLabel(ui_spec.label)
            if ui_spec.tooltip is not None:
                label.setToolTip(ui_spec.tooltip)
            layout.addRow(label, editor.widget())

    @typing.override
    def set_value(self, value: T) -> None:
        for ui_spec in self._ui_specs:
            editor = getattr(self, ui_spec.editor_name)
            assert isinstance(editor, ValueEditor)
            editor.set_value(getattr(value, ui_spec.field_name))

    # TODO: Figure out why pyright report this method as an incompatible override
    @typing.override
    def read_value(self) -> T:  # type: ignore[reportIncompatibleMethodOverride]
        attribute_values = {}
        for ui_spec in self._ui_specs:
            editor = getattr(self, ui_spec.editor_name)
            assert isinstance(editor, ValueEditor)
            attribute_values[ui_spec.field_name] = editor.read_value()
        return self._cls(**attribute_values)

    @typing.override
    def set_editable(self, editable: bool) -> None:
        for ui_spec in self._ui_specs:
            editor = getattr(self, ui_spec.editor_name)
            assert isinstance(editor, ValueEditor)
            editor.set_editable(editable)

    @typing.override
    def widget(self) -> QWidget:
        return self._widget


@attrs.frozen
class AttributeOverride:
    label: str | None = None
    editor_factory: EditorFactory | None = None
    tooltip: str | None = None


@attrs.frozen
class AttributeUIInfo:
    field_name: str
    label: str
    editor_factory: EditorFactory
    tooltip: str | None

    @property
    def editor_name(self) -> str:
        return attr_to_editor_name(self.field_name)


def get_attribute_label(
    attr: attrs.Attribute,
    override: AttributeOverride | None,
) -> str:
    label = None
    if override is not None:
        label = override.label
    if label is None:
        label = prettify_snake_case(attr.name)
    return label


def get_attribute_editor_factory(
    attr: attrs.Attribute,
    override: AttributeOverride | None,
    builder: EditorBuilder,
) -> EditorFactory:
    editor_factory = None
    if override is not None:
        editor_factory = override.editor_factory
    if editor_factory is None:
        if attr.type is None:
            raise ValueError("Attribute has no type annotation")
        editor_factory = builder.build_editor(attr.type)
    return editor_factory


def get_attribute_tooltip(
    attr: attrs.Attribute,
    override: AttributeOverride | None,
) -> str | None:
    tooltip = None
    if override is not None:
        tooltip = override.tooltip
    if tooltip is None:
        tooltip = extract_documentation(attr.type)
    return tooltip


def prettify_snake_case(name: str) -> str:
    if name:
        words = name.split("_")
        words[0] = words[0].title()
        return " ".join(words)
    else:
        return name


def attr_to_editor_name(name: str) -> str:
    return f"editor_{name}"


def extract_documentation(type_: TypeExpr) -> str | None:
    if typing.get_origin(type_) is typing.Annotated:
        for arg in typing.get_args(type_):
            if isinstance(arg, annotated_types.DocInfo):
                return arg.documentation
    return None


class AttributeEditorBuildingError(EditorBuildingError):
    def __init__(self, cls: type[attrs.AttrsInstance], attribute: attrs.Attribute):
        msg = f"Could not build editor for attribute '{attribute.name}' of {cls}"
        super().__init__(msg)
