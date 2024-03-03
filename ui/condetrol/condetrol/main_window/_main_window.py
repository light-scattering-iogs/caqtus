import contextlib
import copy
from collections.abc import Mapping, Callable
from typing import Optional, Literal

from PySide6.QtCore import QSettings, QThread, QObject, QTimer, Signal, Qt, QByteArray
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QLabel,
    QHBoxLayout,
    QWidget, QSplitter, QVBoxLayout, QToolButton,
)

from core.experiment import SequenceInterruptedException
from core.experiment.manager import ExperimentManager, Procedure
from core.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    Sequence,
)
from core.session.sequence import State
from exception_tree import ExceptionDialog
from waiting_widget import run_with_wip_widget
from ._main_window_ui import Ui_CondetrolMainWindow
from ..device_configuration_editors import (
    DeviceConfigurationEditInfo,
    ConfigurationsEditor,
)
from ..icons import get_icon
from ..logger import logger
from ..path_view import EditablePathHierarchyView
from ..sequence_widget import SequenceWidget
from ..timelanes_editor import (
    LaneDelegateFactory,
    default_lane_delegate_factory,
    LaneModelFactory,
    default_lane_model_factory,
)


# noinspection PyTypeChecker
def default_connect_to_experiment_manager() -> ExperimentManager:
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


class CondetrolMainWindow(QMainWindow, Ui_CondetrolMainWindow):
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        device_configuration_editors: (
            Mapping[str, DeviceConfigurationEditInfo] | None
        ) = None,
        connect_to_experiment_manager: Callable[
            [], ExperimentManager
        ] = default_connect_to_experiment_manager,
        model_factory: LaneModelFactory = default_lane_model_factory,
        lane_delegate_factory: LaneDelegateFactory = default_lane_delegate_factory,
        *args,
        **kwargs,
    ):
        """Initialize the main window.

        Args:
            session_maker: A callable that returns an ExperimentSession.
            This is used to access the storage in which to look for sequences to display
            and edit.
            device_configuration_editors: Contains the editors to use to display and
            edit a given device configurations.
            This must be a mapping from strings corresponding to device configuration
            types to device configuration editors.
            When the GUI needs to display an editor for a device configurations, it
            will look up this mapping for an editor matching the configurations type.
            If the configuration type cannot be found in this mapping, the configuration
            editor will just contain a message suggesting to register an editor.
            If you want to be able to edit a device configuration in the GUI, you need
            to have the key corresponding to the configuration type in this mapping.
            connect_to_experiment_manager: A callable that returns an
            ExperimentManager.
            When the user starts a sequence in the GUI, it will call this function to
            connect to the experiment manager and submit the sequence to the manager.
            model_factory: A factory for lane models.
            lane_delegate_factory: A factory for lane delegates.
            *args: Positional arguments for QMainWindow.
            **kwargs: Keyword arguments for QMainWindow.
        """

        super().__init__(*args, **kwargs)
        self._path_view = EditablePathHierarchyView(session_maker, self)
        self._connect_to_experiment_manager = connect_to_experiment_manager
        self.session_maker = session_maker
        self.delegate_factory = lane_delegate_factory
        self.model_factory = model_factory
        if device_configuration_editors is None:
            device_configuration_editors = {}
        self.device_configuration_edit_infos = device_configuration_editors
        self._procedure_watcher_thread = ProcedureWatcherThread(self)
        self.sequence_widget = SequenceWidget(
            self.session_maker, self.model_factory, self.delegate_factory, parent=self
        )
        self.status_widget = IconLabel(icon_position="left")
        self.setup_ui()
        self.restore_window()
        self.setup_connections()
        self._exit_stack = contextlib.ExitStack()

    def __enter__(self):
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._path_view)
        self._exit_stack.enter_context(self.sequence_widget)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        return self._exit_stack.__exit__(exc_type, exc_value, exc_tb)

    def setup_ui(self):
        self.setupUi(self)
        splitter = QSplitter(self)
        splitter.addWidget(self._path_view)
        splitter.addWidget(self.sequence_widget)
        splitter.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(splitter)
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

    def open_device_configurations_editor(self):
        with self.session_maker() as session:
            previous_device_configurations = dict(session.default_device_configurations)
        configurations_editor = ConfigurationsEditor(
            copy.deepcopy(previous_device_configurations),
            self.device_configuration_edit_infos,
        )
        configurations_editor.exec()
        new_device_configurations = dict(configurations_editor.device_configurations)
        with self.session_maker() as session:
            for device_name in session.default_device_configurations:
                if device_name not in new_device_configurations:
                    del session.default_device_configurations[device_name]
            for (
                device_name,
                device_configuration,
            ) in new_device_configurations.items():
                session.default_device_configurations[
                    device_name
                ] = device_configuration

    def closeEvent(self, a0):
        self.save_window()
        super().closeEvent(a0)

    def restore_window(self) -> None:
        """Restore the window state and geometry from the app settings."""

        ui_settings = QSettings()
        state = ui_settings.value(f"{__name__}/state", defaultValue=None)
        if isinstance(state, QByteArray):
            self.restoreState(state)
        geometry = ui_settings.value(f"{__name__}/geometry", defaultValue=None)
        if isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)

    def save_window(self) -> None:
        """Save the window state and geometry to the app settings."""

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
