import sys
from collections.abc import Callable

import qtawesome
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

import caqtus.gui.condetrol.ressources  # noqa
from caqtus.experiment_control import ExperimentManager
from caqtus.session import ExperimentSessionMaker
from .device_configuration_editors import DeviceConfigurationsPlugin
from .main_window import CondetrolMainWindow
from .timelanes_editor import TimeLanesPlugin, default_time_lanes_plugin
from ..qtutil import QtAsyncio


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
        time_lanes_plugin: TimeLanesPlugin = default_time_lanes_plugin,
        device_configurations_plugin: DeviceConfigurationsPlugin = DeviceConfigurationsPlugin.default(),
    ):
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
            time_lanes_plugin=time_lanes_plugin,
            device_configurations_plugin=device_configurations_plugin,
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
                    app.quit()
            finally:
                sys.__excepthook__(*args)

        sys.excepthook = excepthook

        self.window.show()
        QtAsyncio.run(self.window.run_async())
