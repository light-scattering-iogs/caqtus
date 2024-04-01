import asyncio

from PySide6.QtCore import Qt, QObject, QTimer, Signal
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


class AsyncioHelper(QObject):
    finished = Signal()

    def __init__(self):
        super().__init__()

    def start(self, coro):
        self.awaitable = coro
        timer = QTimer(self)
        timer.singleShot(0, self.run)

    def run(self):
        async def wrapped():
            await self.awaitable
            self.finished.emit()

        event_loop = asyncio.get_event_loop()
        asyncio.ensure_future(wrapped(), loop=event_loop)
