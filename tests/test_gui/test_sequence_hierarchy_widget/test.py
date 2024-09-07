from PySide6.QtCore import Qt
from pytestqt.modeltest import ModelTester

from caqtus.gui._common.sequence_hierarchy import AsyncPathHierarchyModel
from caqtus.gui.qtutil import qt_trio
from caqtus.session import PureSequencePath, State


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


def test_2(
    session_maker, qtmodeltester: ModelTester, steps_configuration, time_lanes, qtbot
):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        path = PureSequencePath(r"\test")
        session.sequences.create(path, steps_configuration, time_lanes)
    qtmodeltester.check(model)
    index = model.index(0, 1)
    assert index.data().state == State.DRAFT

    with session_maker() as session:
        session.sequences.set_state(path, State.PREPARING)

    qt_trio.run(model.update_stats, model.index(0, 0))
    assert index.data().state == State.PREPARING
