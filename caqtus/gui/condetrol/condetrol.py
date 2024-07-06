import sys
from collections.abc import Callable
from typing import Optional

import qtawesome
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

import caqtus.gui.condetrol.ressources  # noqa
from caqtus.experiment_control import ExperimentManager
from caqtus.session import ExperimentSessionMaker
from .extension import CondetrolExtension, CondetrolExtensionProtocol
from .main_window import CondetrolMainWindow
from .main_window._main_window import CondetrolWindowHandler
from ..qtutil import qt_trio


# noinspection PyTypeChecker
def default_connect_to_experiment_manager() -> ExperimentManager:
    """Raise an error when trying to connect to an experiment manager."""

    error = NotImplementedError("Not implemented.")
    error.add_note(
        f"You need to provide a function to connect to the experiment "
        f"manager when initializing the main window."
    )
    error.add_note(
        "It is not possible to run sequences without connecting to an experiment "
        "manager."
    )
    raise error


class Condetrol:
    """A utility class to launch the Condetrol GUI.

    This class is a convenience wrapper around the :class:`CondetrolMainWindow` class.
    It sets up the application and launches the main window.

    See :class:`CondetrolMainWindow` for more information on the parameters.
    """

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        connect_to_experiment_manager: Callable[
            [], ExperimentManager
        ] = default_connect_to_experiment_manager,
        extension: Optional[CondetrolExtensionProtocol] = None,
    ):
        self.session_maker = session_maker
        if extension is None:
            extension = CondetrolExtension()
        app = QApplication.instance()
        if app is None:
            self.app = QApplication([])
            self.app.setOrganizationName("Caqtus")
            self.app.setApplicationName("Condetrol")
            self.app.setWindowIcon(
                qtawesome.icon("mdi6.cactus", size=64, color="green")
            )
            self.app.setStyle("Fusion")
        else:
            self.app = app

        QFontDatabase.addApplicationFont(":/fonts/JetBrainsMono-Regular.ttf")

        self.window = CondetrolMainWindow(
            session_maker=session_maker,
            connect_to_experiment_manager=connect_to_experiment_manager,
            extension=extension,
        )

    def run(self) -> None:
        """Launch the Condetrol GUI.

        This method will block until the GUI is closed by the user.
        """

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
        sys.excepthook = excepthook

        async def run_condetrol():
            handler = CondetrolWindowHandler(self.window, self.session_maker)
            await handler.run_async()

        try:
            qt_trio.run(run_condetrol)
        finally:
            sys.excepthook = previous_excepthook
