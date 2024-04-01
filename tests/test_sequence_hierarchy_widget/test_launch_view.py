from pytestqt.modeltest import ModelTester
from pytestqt.qtbot import QtBot

from caqtus.gui.common.sequence_hierarchy import (
    AsyncPathHierarchyModel,
)
from caqtus.gui.common.sequence_hierarchy.view import AsyncPathHierarchyView
from caqtus.session import PureSequencePath
from .session_maker import session_maker


def test_0(session_maker, qtmodeltester: ModelTester, qtbot: QtBot):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        session.paths.create_path(PureSequencePath(r"\test\a"))
    qtmodeltester.check(model)

    view = AsyncPathHierarchyView(session_maker)
    view.show()

    view.show()
    qtbot.addWidget(view)
    # qtbot.stop()
