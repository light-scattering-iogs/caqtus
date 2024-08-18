from caqtus.gui._common.sequence_hierarchy import AsyncPathHierarchyModel
from caqtus.gui.qtutil import qt_trio
from caqtus.session import PureSequencePath
from tests.fixtures import steps_configuration, time_lanes
from .session_maker import session_maker


def test_0(session_maker, qtmodeltester, qtbot):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        path = PureSequencePath(r"\test")
        session.paths.create_path(path)
    qtmodeltester.check(model)

    with session_maker() as session:
        session.paths.delete_path(path)

    qt_trio.run(model.prune)
    assert model.rowCount() == 0


def test_1(session_maker, qtmodeltester, qtbot):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        path = PureSequencePath(r"\a\b")
        session.paths.create_path(path)
    qtmodeltester.check(model)

    with session_maker() as session:
        session.paths.delete_path(path)

    qt_trio.run(model.prune)
    assert model.rowCount() == 1

    with session_maker() as session:
        path = PureSequencePath(r"\a")
        session.paths.delete_path(path)

    qt_trio.run(model.prune)

    assert model.rowCount() == 0


def test_2(session_maker, qtmodeltester, steps_configuration, time_lanes, qtbot):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        path = PureSequencePath(r"\a")
        session.paths.create_path(path)
    qtmodeltester.check(model)

    with session_maker() as session:
        session.sequences.create(path, steps_configuration, time_lanes)

    qt_trio.run(model.prune)
    assert model.rowCount() == 1


def test_3(session_maker, qtmodeltester, steps_configuration, time_lanes, qtbot):
    model = AsyncPathHierarchyModel(session_maker)
    with session_maker() as session:
        path = PureSequencePath(r"\a")
        session.paths.create_path(path)
    qtmodeltester.check(model)

    child = model.index(0, 0)

    with session_maker() as session:
        session.paths.delete_path(path)

    qt_trio.run(model.prune, child)
    assert model.rowCount() == 0
