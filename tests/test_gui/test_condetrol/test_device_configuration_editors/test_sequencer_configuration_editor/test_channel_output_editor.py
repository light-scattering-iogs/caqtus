from caqtus.device.sequencer.channel_commands import Constant
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor.channel_output_editor import (
    ChannelOutputEditor,
)
from caqtus.types.expression import Expression


def test(qtbot):
    output = Constant(Expression("1"))
    editor = ChannelOutputEditor(output)
    qtbot.addWidget(editor)
    editor.show()
    assert editor.get_output() == output
