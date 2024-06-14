from pytestqt.qtbot import QtBot

from caqtus.gui.condetrol.sequence_iteration_editors import StepsIterationEditor
from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    VariableDeclaration,
    LinspaceLoop,
    ExecuteShot,
)
from caqtus.types.variable_name import DottedVariableName


def test(qtbot: QtBot):
    # Simple instantiation test that can also be used to screenshot the widget for the
    # documentation.
    editor = StepsIterationEditor()
    steps = StepsConfiguration(
        [
            VariableDeclaration(DottedVariableName("a"), Expression("1")),
            LinspaceLoop(
                variable=DottedVariableName("b"),
                start=Expression("0"),
                stop=Expression("1"),
                num=10,
                sub_steps=[ExecuteShot()],
            ),
        ]
    )
    editor.set_iteration(steps)

    qtbot.addWidget(editor)

    editor.show()
