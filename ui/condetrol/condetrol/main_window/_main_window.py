import copy
import functools
import logging
import traceback
from collections.abc import Mapping, Callable
from typing import Optional

import pyqtgraph.dockarea
from PyQt6.QtCore import QSettings, QThread, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from core.device import DeviceName, DeviceConfigurationAttrs
from core.experiment.manager import ExperimentManager, Procedure
from core.session import ExperimentSessionMaker, PureSequencePath, ConstantTable
from waiting_widget import run_with_wip_widget
from ._main_window_ui import Ui_CondetrolMainWindow
from ..app_name import APPLICATION_NAME
from ..constant_tables_editor import ConstantTablesEditor
from ..device_configuration_editors import (
    DeviceConfigurationEditInfo,
    ConfigurationsEditor,
)
from ..path_view import EditablePathHierarchyView
from ..sequence_widget import SequenceWidget

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CondetrolMainWindow(QMainWindow, Ui_CondetrolMainWindow):
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        device_configuration_editors: Mapping[str, DeviceConfigurationEditInfo],
        connect_to_experiment_manager: Callable[[], ExperimentManager],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._path_view = EditablePathHierarchyView(session_maker)
        self._connect_to_experiment_manager = connect_to_experiment_manager
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.session_maker = session_maker
        self.device_configuration_edit_infos = device_configuration_editors
        self._procedure_watcher_thread = ProcedureWatcherThread(self)
        self.setup_ui()
        self.restore_window_state()
        self.setup_connections()

    def __enter__(self):
        self._path_view.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        return self._path_view.__exit__(exc_type, exc_value, exc_tb)

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
        self.action_edit_constants.triggered.connect(self.open_constants_editor)
        self._path_view.sequence_double_clicked.connect(self.open_sequence_editor)
        self._procedure_watcher_thread.exception_occurred.connect(
            self.on_procedure_exception
        )

    def open_sequence_editor(self, path: PureSequencePath):
        editor = SequenceWidget(path, self.session_maker)
        editor.sequence_start_requested.connect(self.start_sequence)

        dock = pyqtgraph.dockarea.Dock(str(path), widget=editor, closable=True)
        self.dock_area.addDock(dock, "right")

    def start_sequence(self, path: PureSequencePath):
        try:
            experiment_manager = run_with_wip_widget(
                self,
                "Connecting to experiment manager...",
                self._connect_to_experiment_manager,
            )
        except Exception as e:
            self.display_error("Failed to connect to experiment manager.", e)
            return
        with experiment_manager.create_procedure(
            "sequence launched from GUI"
        ) as procedure:
            try:
                procedure.start_sequence(path)
            except Exception as e:
                self.display_error(
                    f"An error occurred while starting the sequence {path}.", e
                )
            self._procedure_watcher_thread.set_procedure(procedure)
            assert not self._procedure_watcher_thread.isRunning()
            self._procedure_watcher_thread.start()

    def on_procedure_exception(self, procedure: Procedure):
        exception = procedure.exception()
        assert exception is not None
        sequences = procedure.sequences()
        assert sequences
        last_sequence = sequences[-1]
        self.display_error(
            f"An error occurred while running the sequence '{last_sequence}'.",
            exception,
        )

    def open_constants_editor(self):
        with self.session_maker() as session:
            previous_constants = dict(session.constants)
        constants_editor = ConstantTablesEditor(copy.deepcopy(previous_constants))
        constants_editor.exec()
        self.update_constant_tables(previous_constants, constants_editor.tables)

    def update_constant_tables(
        self,
        previous_tables: Mapping[str, ConstantTable],
        new_tables: Mapping[str, ConstantTable],
    ):
        to_remove = set(previous_tables) - set(new_tables)
        to_add = set(new_tables) - set(previous_tables)
        in_both = set(previous_tables) & set(new_tables)
        to_update = {
            table_name
            for table_name in in_both
            if new_tables[table_name] != previous_tables[table_name]
        }
        with self.session_maker() as session:
            for table_name in to_remove:
                del session.constants[table_name]
            for table_name in to_add | to_update:
                session.constants[table_name] = new_tables[table_name]

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

    def closeEvent(self, a0):
        self.save_window_state()
        super().closeEvent(a0)

    def restore_window_state(self):
        ui_settings = QSettings()
        state = ui_settings.value(f"{__name__}/state")
        if state is not None:
            self.restoreState(state)
        geometry = ui_settings.value(f"{__name__}/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def save_window_state(self):
        ui_settings = QSettings()
        ui_settings.setValue(f"{__name__}/state", self.saveState())
        ui_settings.setValue(f"{__name__}/geometry", self.saveGeometry())

    def display_error(self, message: str, exception: Exception):
        logger.error(message, exc_info=exception)
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Critical)
        message_box.setText(f"{message}\n\n{exception}")
        detail = traceback.format_exception(exception)
        message_box.setDetailedText("".join(detail))
        message_box.setWindowTitle("Error")
        message_box.exec()


class ProcedureWatcherThread(QThread):
    exception_occurred = pyqtSignal(Procedure)

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._procedure: Optional[Procedure] = None

    def set_procedure(self, procedure: Procedure):
        self._procedure = procedure

    def run(self):
        timer = QTimer()

        def watch():
            assert self._procedure is not None
            if self._procedure.is_active():
                return
            else:
                if self._procedure.exception() is not None:
                    self.exception_occurred.emit(self._procedure)
                self._procedure = None
                self.quit()

        timer.timeout.connect(watch)  # type: ignore
        timer.start(50)
        self.exec()
        timer.stop()
