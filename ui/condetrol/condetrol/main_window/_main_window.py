import copy
from collections.abc import Mapping

import pyqtgraph.dockarea
from PyQt6.QtWidgets import QMainWindow, QWidget

from core.device import DeviceName, DeviceConfigurationAttrs
from core.session import ExperimentSessionMaker, PureSequencePath
from ._main_window_ui import Ui_CondetrolMainWindow
from ..app_name import APPLICATION_NAME
from ..device_configuration_editors import (
    DeviceConfigurationEditInfo,
    ConfigurationsEditor,
)
from ..path_view import EditablePathHierarchyView
from ..sequence_widget import SequenceWidget


class CondetrolMainWindow(QMainWindow, Ui_CondetrolMainWindow):
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        device_configuration_editors: Mapping[str, DeviceConfigurationEditInfo],
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._path_view = EditablePathHierarchyView(session_maker)
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.session_maker = session_maker
        self.device_configuration_edit_infos = device_configuration_editors
        self.setup_ui()
        self.setup_connections()

    def __enter__(self):
        self._path_view.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._path_view.__exit__(exc_type, exc_value, traceback)

    def setup_ui(self):
        self.setupUi(self)
        self.setCentralWidget(self.dock_area)
        dock = pyqtgraph.dockarea.Dock("Sequences")
        dock.addWidget(self._path_view)
        self.dock_area.addDock(dock, "left")
        self.setWindowTitle(APPLICATION_NAME)

    def setup_connections(self):
        self.action_edit_device_configurations.triggered.connect(
            self.open_device_configurations_editor
        )
        self._path_view.sequence_double_clicked.connect(self.open_sequence_editor)

    def open_sequence_editor(self, path: PureSequencePath):
        editor = SequenceWidget()
        dock = pyqtgraph.dockarea.Dock(str(path), widget=editor, closable=True)
        self.dock_area.addDock(dock, "right")

    def open_device_configurations_editor(self):
        with self.session_maker() as session:
            previous_device_configurations = dict(session.device_configurations)
        configurations_editor = ConfigurationsEditor(
            copy.deepcopy(previous_device_configurations),
            self.device_configuration_edit_infos,
        )
        configurations_editor.exec()
        self.update_device_configurations(
            previous_device_configurations, configurations_editor.device_configurations
        )

    def update_device_configurations(
        self,
        previous_device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
        new_device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ):
        to_remove = set(previous_device_configurations) - set(new_device_configurations)
        to_add = set(new_device_configurations) - set(previous_device_configurations)
        in_both = set(previous_device_configurations) & set(new_device_configurations)
        to_update = {
            device_name
            for device_name in in_both
            if new_device_configurations[device_name]
            != previous_device_configurations[device_name]
        }
        with self.session_maker() as session:
            for device_name in to_remove:
                del session.device_configurations[device_name]
            for device_name in to_add | to_update:
                session.device_configurations[device_name] = new_device_configurations[
                    device_name
                ]
