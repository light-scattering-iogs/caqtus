from caqtus.gui.common.sequence_hierarchy import AsyncPathHierarchyModel
from .session_maker import session_maker
from pytestqt.modeltest import ModelTester


def test_0(session_maker, qtmodeltester: ModelTester):
    model = AsyncPathHierarchyModel(session_maker)
    qtmodeltester.check(model)
