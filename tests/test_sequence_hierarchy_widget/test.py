from PySide6.QtCore import Qt
from pytestqt.modeltest import ModelTester

from caqtus.gui.common.sequence_hierarchy import AsyncPathHierarchyModel
from caqtus.session import PureSequencePath
from .session_maker import session_maker


def test_0(session_maker, qtmodeltester: ModelTester):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        session.paths.create_path(PureSequencePath(r"\test"))
    qtmodeltester.check(model)


def test_1(session_maker, qtmodeltester: ModelTester):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        session.paths.create_path(PureSequencePath(r"\test\test2"))
    qtmodeltester.check(model)
    assert model.rowCount() == 1
    child = model.index(0, 0)
    assert model.rowCount(child) == 1
    assert model.data(child, Qt.ItemDataRole.DisplayRole) == "test"
    child = model.index(0, 0, child)
    assert model.data(child, Qt.ItemDataRole.DisplayRole) == "test2"


# def test_2(session_maker, qtbot: QtBot):
#     with session_maker() as session:
#         for i in range(1000):
#             session.paths.create_path(PureSequencePath(rf"\test\a\test{i}"))
#     model = AsyncPathHierarchyModel(session_maker)
#     view = QTreeView()
#     qtbot.addWidget(view)
#     view.setModel(model)
#     view.show()
#
#     qtbot.stop()
