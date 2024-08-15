from collections.abc import Mapping, Callable

import qtawesome
from PySide6.QtWidgets import QApplication

from caqtus.session import ExperimentSessionMaker
from caqtus.utils.serialization import JSON
from .single_shot_widget import (
    SnapShotMainWindow,
    ViewCreator,
    ShotView,
    SnapShotWindowHandler,
)
from ..._common.sequence_hierarchy import AsyncPathHierarchyView
from ...qtutil import qt_trio


class SnapShot:
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        view_creators: Mapping[str, ViewCreator],
        view_dumper: Callable[[ShotView], JSON],
        view_loader: Callable[[JSON], ShotView],
    ):
        app = QApplication.instance()
        self.session_maker = session_maker
        if app is None:
            self.app = QApplication([])
            self.app.setOrganizationName("Caqtus")
            self.app.setApplicationName("Shot Viewer")
            self.app.setWindowIcon(
                qtawesome.icon("mdi6.microscope", size=64, color="grey")
            )
            self.app.setStyle("Fusion")
        else:
            self.app = app

        hierarchy_view = AsyncPathHierarchyView(session_maker)

        self.window = SnapShotMainWindow(
            hierarchy_view=hierarchy_view,
            view_creators=view_creators,
            view_dumper=view_dumper,
            view_loader=view_loader,
        )

    def run(self) -> None:
        self.window.show()

        async def handle():
            handler = SnapShotWindowHandler(self.window, self.session_maker)
            await handler.exec_async()

        qt_trio.run(handle)
