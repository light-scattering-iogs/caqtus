import warnings
from typing import Optional, assert_never

from caqtus.experiment_control.manager import (
    LocalExperimentManager,
    RemoteExperimentManagerClient,
)
from caqtus.gui.condetrol import Condetrol
from caqtus.session.sql import PostgreSQLConfig, PostgreSQLExperimentSessionMaker
from ._caqtus_extension import CaqtusExtension
from .device_extension import DeviceExtension
from .time_lane_extension import TimeLaneExtension
from ..experiment_control import ExperimentManager
from ..experiment_control.manager import (
    ExperimentManagerConnection,
    LocalExperimentManagerConfiguration,
    RemoteExperimentManagerConfiguration,
)


class CaqtusInjector:
    """Dispatches configuration and extensions to the appropriate components.

    There should be only a single instance of this class in the entire application.
    It is used to configure the experiment and knows how to launch the different
    components of the application with the dependency extracted from the configuration.
    """

    def __init__(self):
        self._session_maker_config: Optional[PostgreSQLConfig] = None
        self._extension = CaqtusExtension()
        self._experiment_manager: Optional[LocalExperimentManager] = None
        self._experiment_manager_location: ExperimentManagerConnection = (
            LocalExperimentManagerConfiguration()
        )

    def configure_storage(self, backend_config: PostgreSQLConfig):
        if self._session_maker_config is not None:
            warnings.warn("Storage configuration is being overwritten.")
        self._session_maker_config = backend_config

    def configure_experiment_manager(self, location: ExperimentManagerConnection):
        self._experiment_manager_location = location

    def register_device_extension(self, device_extension: DeviceExtension) -> None:
        self._extension.register_device_extension(device_extension)

    def register_time_lane_extension(
        self, time_lane_extension: TimeLaneExtension
    ) -> None:
        self._extension.register_time_lane_extension(time_lane_extension)

    def get_session_maker(self) -> PostgreSQLExperimentSessionMaker:
        if self._session_maker_config is None:
            error = RuntimeError("Storage configuration has not been set.")
            error.add_note(
                "Please call `configure_storage` with the appropriate configuration."
            )
            raise error
        session_maker = self._extension.create_session_maker(
            PostgreSQLExperimentSessionMaker,
            config=self._session_maker_config,
        )
        return session_maker

    def connect_to_experiment_manager(self) -> ExperimentManager:
        location = self._experiment_manager_location
        if isinstance(location, LocalExperimentManagerConfiguration):
            return self.get_local_experiment_manager()
        elif isinstance(location, RemoteExperimentManagerConfiguration):
            client = RemoteExperimentManagerClient(
                address=(location.address, location.port),
                authkey=bytes(location.authkey, "utf-8"),
            )
            return client.get_experiment_manager()
        else:
            assert_never(location)

    def get_local_experiment_manager(self) -> LocalExperimentManager:
        if self._experiment_manager is None:
            _experiment_manager = LocalExperimentManager(
                session_maker=self.get_session_maker(), device_server_configs={}
            )
        return self._experiment_manager

    def launch_condetrol(self) -> None:
        app = Condetrol(
            self.get_session_maker(),
            connect_to_experiment_manager=self.connect_to_experiment_manager,
            extension=self._extension.condetrol_extension,
        )
        app.run()
