import sys
from collections.abc import Mapping, Callable

import qtawesome
from PySide6.QtWidgets import QApplication

from caqtus.session import ExperimentSessionMaker
from caqtus.utils.serialization import JSON
from .single_shot_widget import ShotViewerMainWindow, ViewCreator, ShotView
from ...qtutil import QtAsyncio


class ShotViewer:
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        view_creators: Mapping[str, ViewCreator],
        view_dumper: Callable[[ShotView], JSON],
        view_loader: Callable[[JSON], ShotView],
    ):
        app = QApplication.instance()
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

        self.window = ShotViewerMainWindow(
            experiment_session_maker=session_maker,
            view_creators=view_creators,
            view_dumper=view_dumper,
            view_loader=view_loader,
        )

    def run(self) -> None:
        # We set up a custom exception hook to close the application if an error occurs.
        # By default, PySide only prints exceptions and doesn't close the app on error.

        def excepthook(*args):
            try:
                app = QApplication.instance()
                if app is not None:
                    app.exit(-1)
            finally:
                sys.__excepthook__(*args)

        self.window.show()

        previous_excepthook = sys.excepthook

        try:
            sys.excepthook = excepthook
            QtAsyncio.run(self.window.exec_async(), keep_running=False)
        finally:
            sys.excepthook = previous_excepthook
