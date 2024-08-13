from collections.abc import Callable

import qtawesome
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

import caqtus.gui.condetrol._ressources  # noqa
from caqtus.experiment_control import ExperimentManager
from caqtus.session import ExperimentSessionMaker
from ._extension import CondetrolExtensionProtocol
from ._main_window import CondetrolMainWindow, CondetrolWindowHandler
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
        extension: CondetrolExtensionProtocol,
        connect_to_experiment_manager: Callable[
            [], ExperimentManager
        ] = default_connect_to_experiment_manager,
    ):
        self.session_maker = session_maker
        app = QApplication.instance()
        if app is None:
            self.app = QApplication([])
        else:
            self.app = app
        self.app.setOrganizationName("Caqtus")
        self.app.setApplicationName("Condetrol")
        self.app.setWindowIcon(qtawesome.icon("mdi6.cactus", size=64, color="green"))
        self.app.setStyle("Fusion")

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

        self.window.show()

        async def run_condetrol():
            handler = CondetrolWindowHandler(self.window, self.session_maker)
            await handler.run_async()

        qt_trio.run(run_condetrol)
