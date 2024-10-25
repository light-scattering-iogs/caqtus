from caqtus.gui.condetrol.device_configuration_editors._autogen import (
    EditorBuilder,
    StringEditor,
)


def test_dispatch_simple_type():
    builder = EditorBuilder()
    builder.register_editor_for_type(str, StringEditor)
    assert builder.build_editor_for_type(str) == StringEditor
