from caqtus.gui.condetrol.device_configuration_editors import ConfigurationsEditor
from pytestqt.qtbot import QtBot


def test(qtbot: QtBot):
    editor = ConfigurationsEditor({}, {})
    qtbot.addWidget(editor)
