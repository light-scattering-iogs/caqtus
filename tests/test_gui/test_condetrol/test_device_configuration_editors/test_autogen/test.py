import attrs
import pytest
from pytestqt.qtbot import QtBot

from caqtus.gui.condetrol.device_configuration_editors._autogen import (
    EditorBuilder,
    StringEditor,
    TypeNotRegisteredError,
    IntegerEditor,
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
    builder.register_editor_for_type(int, IntegerEditor)

    @attrs.define
    class MyClass:
        number: int
        channel_0: str
        channel_1: str

    MyClassEditor = builder.build_editor(MyClass)  # noqa: N806

    initial_value = MyClass(42, "abc", "test")

    editor = MyClassEditor(initial_value)
    widget = editor.widget()
    qtbot.add_widget(widget)
    editor.set_editable(False)
    editor_channel_0 = getattr(editor, "editor_channel_0")  # noqa: B009
    assert isinstance(editor_channel_0, StringEditor)
    editor_channel_0.widget().setText("check")
    assert editor.read_value() == MyClass(42, "check", "test")


def test_nested_class(qtbot: QtBot):
    builder = EditorBuilder()
    builder.register_editor_for_type(str, StringEditor)
    builder.register_editor_for_type(int, IntegerEditor)

    @attrs.define
    class Child:
        age: int

    @attrs.define
    class Parent:
        name: str
        child: Child

    initial_value = Parent(name="Julia", child=Child(age=8))

    ParentEditor = builder.build_editor(Parent)  # noqa: N806
    editor = ParentEditor(initial_value)
    widget = editor.widget()
    qtbot.add_widget(widget)
    editor.set_editable(True)
    assert editor.read_value() == initial_value
    widget.show()
    qtbot.stop()
