import asyncio
import contextlib
from collections.abc import Callable
from typing import Optional, Literal

from PySide6.QtCore import QSettings, QThread, QObject, QTimer, Signal, Qt
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QLabel,
    QHBoxLayout,
    QWidget,
    QDockWidget,
    QDialog,
)

from caqtus.experiment_control import SequenceInterruptedException
from caqtus.experiment_control.manager import ExperimentManager, Procedure
from caqtus.gui.common.exception_tree import ExceptionDialog
from caqtus.gui.common.waiting_widget import run_with_wip_widget
from caqtus.gui.condetrol.parameter_tables_editor import ParameterNamespaceEditor
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    Sequence,
    ParameterNamespace,
)
from caqtus.session.sequence import State
from ._main_window_ui import Ui_CondetrolMainWindow
from ..device_configuration_editors import (
    DeviceConfigurationsDialog,
    DeviceConfigurationsPlugin,
)
from ..icons import get_icon
from ..logger import logger
from ..path_view import EditablePathHierarchyView
from ..sequence_widget import SequenceWidget
from ..timelanes_editor import TimeLanesPlugin


class CondetrolMainWindow(QMainWindow, Ui_CondetrolMainWindow):
    """The main window of the Condetrol GUI.

    Parameters
    ----------
    session_maker
        A callable that returns an ExperimentSession.
        This is used to access the storage in which to look for sequences to display
        and edit.
    connect_to_experiment_manager
        A callable that is called to connect to an experiment manager in charge of
        running sequences.
        This is used to submit sequences to the manager when the user starts them
        in the GUI.
    time_lanes_plugin
        The plugin to use for customizing the time lane editor.
    device_configurations_plugin
        A plugin that provides a way to create, display and edit the device
        configurations.
    """

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        connect_to_experiment_manager: Callable[[], ExperimentManager],
        time_lanes_plugin: TimeLanesPlugin,
        device_configurations_plugin: DeviceConfigurationsPlugin,
    ):
        super().__init__()
        self._path_view = EditablePathHierarchyView(session_maker, self)
        self._global_parameters_editor = ParameterNamespaceEditor()
        self._connect_to_experiment_manager = connect_to_experiment_manager
        self.session_maker = session_maker
        self._procedure_watcher_thread = ProcedureWatcherThread(self)
        self.sequence_widget = SequenceWidget(
            self.session_maker, time_lanes_plugin, parent=self
        )
        self.status_widget = IconLabel(icon_position="left")
        self.device_configurations_dialog = DeviceConfigurationsDialog(
            device_configurations_plugin, parent=self
        )
        self.setup_ui()
        self.restore_window()
        self.setup_connections()
        self._exit_stack = contextlib.ExitStack()
        self._task_group = asyncio.TaskGroup()

    async def run_async(self) -> None:
        """Run the main window asynchronously."""

        async with self._task_group:
            self._task_group.create_task(self._path_view.run_async())
            self._task_group.create_task(self._monitor_global_parameters())
            self._task_group.create_task(self.sequence_widget.exec_async())

    def setup_ui(self):
        self.setupUi(self)
        self.setCentralWidget(self.sequence_widget)
        paths_dock = QDockWidget("Sequences", self)
        paths_dock.setObjectName("SequencesDock")
        paths_dock.setWidget(self._path_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, paths_dock)
        self.dock_menu.addAction(paths_dock.toggleViewAction())
        global_parameters_dock = QDockWidget("Global parameters", self)
        global_parameters_dock.setWidget(self._global_parameters_editor)
        global_parameters_dock.setObjectName("GlobalParametersDock")
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, global_parameters_dock
        )
        self.dock_menu.addAction(global_parameters_dock.toggleViewAction())
        # We hide the global parameters dock by default to reduce clutter when
        # launching the app the first time.
        global_parameters_dock.hide()
        self.statusBar().addPermanentWidget(self.status_widget)

    def setup_connections(self):
        self.action_edit_device_configurations.triggered.connect(
            self.open_device_configurations_editor
        )
        self._path_view.sequence_double_clicked.connect(self.set_edited_sequence)
        self._path_view.sequence_start_requested.connect(self.start_sequence)
        self._path_view.sequence_interrupt_requested.connect(self.interrupt_sequence)
        self._procedure_watcher_thread.exception_occurred.connect(
            self.on_procedure_exception
        )
        self.sequence_widget.sequence_changed.connect(self.on_viewed_sequence_changed)
        self.sequence_widget.sequence_start_requested.connect(self.start_sequence)
        self._global_parameters_editor.parameters_edited.connect(
            self._on_global_parameters_edited
        )

    def on_viewed_sequence_changed(
        self, sequence: Optional[tuple[PureSequencePath, State]]
    ):
        if sequence is None:
            text = ""
            icon = None
        else:
            path, state = sequence
            text = " > ".join(path.parts)
            color = self.palette().text().color()
            if state.is_editable():
                icon = get_icon("editable-sequence", color=color)
            else:
                icon = get_icon("read-only-sequence", color=color)
        self.status_widget.set_text(text)
        self.status_widget.set_icon(icon)

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

    def open_device_configurations_editor(self) -> None:
        with self.session_maker() as session:
            previous_device_configurations = dict(session.default_device_configurations)
        self.device_configurations_dialog.set_device_configurations(
            previous_device_configurations
        )
        if self.device_configurations_dialog.exec() == QDialog.DialogCode.Accepted:
            new_device_configurations = (
                self.device_configurations_dialog.get_device_configurations()
            )
            with self.session_maker() as session:
                for device_name in session.default_device_configurations:
                    if device_name not in new_device_configurations:
                        del session.default_device_configurations[device_name]
                for (
                    device_name,
                    device_configuration,
                ) in new_device_configurations.items():
                    session.default_device_configurations[device_name] = (
                        device_configuration
                    )

    def closeEvent(self, a0):
        self.save_window()
        super().closeEvent(a0)

    def restore_window(self) -> None:
        ui_settings = QSettings()
        state = ui_settings.value(f"{__name__}/state", defaultValue=None)
        if state is not None:
            self.restoreState(state)
        geometry = ui_settings.value(f"{__name__}/geometry", defaultValue=None)
        if geometry is not None:
            self.restoreGeometry(geometry)

    def save_window(self) -> None:
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

    def _on_global_parameters_edited(self, parameters: ParameterNamespace) -> None:
        with self.session_maker() as session:
            session.set_global_parameters(parameters)
            logger.info(f"Global parameters written to storage: {parameters}")

    async def _monitor_global_parameters(self) -> None:
        while True:
            parameters = await asyncio.to_thread(
                _get_global_parameters, self.session_maker
            )
            if parameters != self._global_parameters_editor.get_parameters():
                self._global_parameters_editor.set_parameters(parameters)
            await asyncio.sleep(0.2)


def _get_global_parameters(session_maker: ExperimentSessionMaker) -> ParameterNamespace:
    with session_maker() as session:
        return session.get_global_parameters()


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


class IconLabel(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon_position: Literal["left", "right"] = "left",
    ):
        super().__init__(parent)
        self._label = QLabel()
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self._label.setFont(font)
        self._icon = QLabel()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if icon_position == "left":
            layout.addWidget(self._icon)
            layout.addWidget(self._label)
        else:
            layout.addWidget(self._label)
            layout.addWidget(self._icon)
        self.setLayout(layout)

    def set_text(self, text: str):
        self._label.setText(text)

    def set_icon(self, icon: Optional[QIcon]):
        if icon is None:
            self._icon.clear()
        else:
            self._icon.setPixmap(icon.pixmap(20, 20))
