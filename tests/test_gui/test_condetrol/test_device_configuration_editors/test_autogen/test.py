import pytest

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
