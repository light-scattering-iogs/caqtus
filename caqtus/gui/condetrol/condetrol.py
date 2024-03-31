from collections.abc import Callable

import qtawesome
from PySide6.QtWidgets import QApplication

from caqtus.experiment_control import ExperimentManager
from caqtus.session import ExperimentSessionMaker
from .device_configuration_editors import (
    DeviceConfigurationsPlugin,
    default_device_configuration_plugin,
)
from .main_window import CondetrolMainWindow
from .main_window._main_window import default_connect_to_experiment_manager
from .timelanes_editor import TimeLanesPlugin, default_time_lanes_plugin
from ..qtutil import QtAsyncio


class Condetrol:
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        connect_to_experiment_manager: Callable[
            [], ExperimentManager
        ] = default_connect_to_experiment_manager,
        time_lanes_plugin: TimeLanesPlugin = default_time_lanes_plugin,
        device_configurations_plugin: DeviceConfigurationsPlugin = default_device_configuration_plugin,
    ) -> None:
        self.app = QApplication([])
        self.app.setOrganizationName("Caqtus")
        self.app.setApplicationName("Condetrol")
        self.app.setWindowIcon(qtawesome.icon("mdi6.cactus", size=64, color="green"))
        self.app.setStyle("Fusion")
        self.window = CondetrolMainWindow(
            session_maker=session_maker,
            connect_to_experiment_manager=connect_to_experiment_manager,
            time_lanes_plugin=time_lanes_plugin,
            device_configurations_plugin=device_configurations_plugin,
        )

    def run(self) -> None:
        with self.window:
            self.window.show()
            QtAsyncio.run(self.window.run_async())
