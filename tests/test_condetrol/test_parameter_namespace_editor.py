from pytestqt.qtbot import QtBot

from caqtus.gui.condetrol.parameter_tables_editor import ParameterNamespaceEditor
from caqtus.session import ParameterNamespace
from caqtus.types.expression import Expression


def test(qtbot: QtBot):
    parameters = ParameterNamespace.from_mapping(
        {
            "mot_loading": {
                "detuning": Expression("-3 MHz"),
                "duration": Expression("100 ms"),
                "red_frequncy": Expression("1 MHz"),
                "red_power": Expression("0 dB"),
            },
            "b": Expression("2"),
            "c": Expression("3"),
        }
    )

    editor = ParameterNamespaceEditor()
    qtbot.addWidget(editor)

    editor.set_parameters(parameters)

    assert editor.get_parameters() == parameters
