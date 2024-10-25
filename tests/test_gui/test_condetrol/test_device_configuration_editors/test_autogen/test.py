import attrs
import pytest
from pytestqt.qtbot import QtBot

from caqtus.gui.condetrol.device_configuration_editors._autogen import (
    EditorBuilder,
    StringEditor,
    TypeNotRegisteredError,
)


def test_dispatch_simple_type():
    builder = EditorBuilder()
    builder.register_editor_for_type(str, StringEditor)
    assert builder.build_editor_for_type(str) == StringEditor


def test_not_registered_type():
    builder = EditorBuilder()
    with pytest.raises(TypeNotRegisteredError):
        builder.build_editor_for_type(str)


def test_attrs_class(qtbot: QtBot):
    builder = EditorBuilder()
    builder.register_editor_for_type(str, StringEditor)

    @attrs.define
    class MyClass:
        channel_0: str
        channel_1: str

    MyClassEditor = builder.build_editor(MyClass)  # noqa: N806

    initial_value = MyClass("abc", "test")

    editor = MyClassEditor(initial_value)
    widget = editor.widget()
    qtbot.add_widget(widget)
    editor.set_editable(False)
    assert editor.get_value() == initial_value
