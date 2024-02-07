import copy
import logging
from collections.abc import Mapping, Callable
from typing import Optional

from PySide6.QtCore import QSettings, QThread, QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QDockWidget, QLabel, QLineEdit,
)
from core.device import DeviceName, DeviceConfigurationAttrs
from core.experiment import SequenceInterruptedException
from core.experiment.manager import ExperimentManager, Procedure
from core.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    ConstantTable,
    Sequence,
)
from core.session.sequence import State
from waiting_widget import run_with_wip_widget

from ._main_window_ui import Ui_CondetrolMainWindow
from .exception_dialog import ExceptionDialog
from ..constant_tables_editor import ConstantTablesEditor
from ..device_configuration_editors import (
    DeviceConfigurationEditInfo,
    ConfigurationsEditor,
)
from ..path_view import EditablePathHierarchyView
from ..sequence_widget import SequenceWidget
from ..timelanes_editor import (
    LaneDelegateFactory,
    default_lane_delegate_factory,
    LaneModelFactory,
    default_lane_model_factory,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CondetrolMainWindow(QMainWindow, Ui_CondetrolMainWindow):
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        device_configuration_editors: Mapping[str, DeviceConfigurationEditInfo],
        connect_to_experiment_manager: Callable[[], ExperimentManager],
        model_factory: LaneModelFactory = default_lane_model_factory,
        lane_delegate_factory: LaneDelegateFactory = default_lane_delegate_factory,
        *args,
        **kwargs,
    ):
        """Initialize the main window.

        Args:
            session_maker: A callable that returns an ExperimentSession.
            device_configuration_editors: A mapping from device name to device
                configuration editor info.
            connect_to_experiment_manager: A callable that returns an
                ExperimentManager.
            model_factory: A factory for lane models.
            lane_delegate_factory: A factory for lane delegates.
            *args: Positional arguments for QMainWindow.
            **kwargs: Keyword arguments for QMainWindow.
        """
        super().__init__(*args, **kwargs)
        self._path_view = EditablePathHierarchyView(session_maker)
        self._connect_to_experiment_manager = connect_to_experiment_manager
        self.session_maker = session_maker
        self.delegate_factory = lane_delegate_factory
        self.model_factory = model_factory
        self.device_configuration_edit_infos = device_configuration_editors
        self._procedure_watcher_thread = ProcedureWatcherThread(self)
        self.sequence_widget = SequenceWidget(
            self.session_maker, self.model_factory, self.delegate_factory
        )
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
        self.setCentralWidget(self.sequence_widget)
        app = QApplication.instance()
        self.setWindowTitle(app.applicationName())
        dock = QDockWidget("Sequences")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setWidget(self._path_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def setup_connections(self):
        self.action_edit_device_configurations.triggered.connect(
            self.open_device_configurations_editor
        )
        self.action_edit_constants.triggered.connect(self.open_constants_editor)
        self._path_view.sequence_double_clicked.connect(self.set_edited_sequence)
        self._path_view.sequence_start_requested.connect(self.start_sequence)
        self._path_view.sequence_interrupt_requested.connect(self.interrupt_sequence)
        self._procedure_watcher_thread.exception_occurred.connect(
            self.on_procedure_exception
        )
        self.sequence_widget.sequence_changed.connect(self.on_viewed_sequence_changed)

    def on_viewed_sequence_changed(
        self, sequence: Optional[tuple[PureSequencePath, State]]
    ):
        if sequence is None:
            text = ""
        else:
            path, state = sequence
            text = f"{path} [{state}]"
        self.statusBar().showMessage(text)

    def set_edited_sequence(self, path: PureSequencePath):
        self.sequence_widget.set_sequence(path)

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
        if self._procedure_watcher_thread.isRunning():
            self.display_error(
                "A sequence is already running.",
                RuntimeError("A sequence is already running."),
            )
            return
        procedure = experiment_manager.create_procedure(
            "sequence launched from GUI", acquisition_timeout=1
        )
        self._procedure_watcher_thread.set_procedure(procedure)
        self._procedure_watcher_thread.set_sequence(Sequence(path))

        self._procedure_watcher_thread.start()

    def on_procedure_exception(self, exception: Exception):
        self.display_error(
            f"An error occurred while running a sequence.",
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
        exception_dialog = ExceptionDialog(self)
        exception_dialog.set_exception(exception)
        exception_dialog.set_message(message)
        exception_dialog.exec()

    def interrupt_sequence(self, path: PureSequencePath):
        experiment_manager = run_with_wip_widget(
            self,
            "Connecting to experiment manager...",
            self._connect_to_experiment_manager,
        )
        # we're actually lying here because we interrupt the running procedure, which
        # may be different from the one passed in argument.
        experiment_manager.interrupt_running_procedure()


class ProcedureWatcherThread(QThread):
    exception_occurred = Signal(Exception)

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._procedure: Optional[Procedure] = None
        self._sequence: Optional[Sequence] = None

    def set_procedure(self, procedure: Procedure):
        self._procedure = procedure

    def set_sequence(self, sequence: Sequence):
        self._sequence = sequence

    def run(self):
        def watch():
            assert self._procedure is not None
            if self._procedure.is_running_sequence():
                return
            else:
                if (exc := self._procedure.exception()) is not None:
                    # Here we ignore the SequenceInterruptedException because it is
                    # expected to happen when the sequence is interrupted and we don't
                    # want to display it to the user as an actual error.
                    if isinstance(exc, SequenceInterruptedException):
                        exc = None
                    elif isinstance(exc, ExceptionGroup):
                        _, exc = exc.split(SequenceInterruptedException)
                    if exc is not None:
                        self.exception_occurred.emit(exc)
                self.quit()

        timer = QTimer()
        timer.timeout.connect(watch)  # type: ignore
        with self._procedure as procedure:
            timer.start(50)
            try:
                procedure.start_sequence(self._sequence)
            except Exception as e:
                exception = RuntimeError(
                    f"An error occurred while starting the sequence {self._sequence}."
                )
                exception.__cause__ = e
                self.exception_occurred.emit(exception)
            self.exec()
        self._procedure = None
        self._sequence = None
        timer.stop()
