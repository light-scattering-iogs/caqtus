import copy
import logging

from concurrent_updater import ConcurrentUpdater
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CurrentExperimentConfigWatcher:
    def __init__(self, session_maker: ExperimentSessionMaker):
        self._session = session_maker()
        with self._session:
            self._config_name = self._session.experiment_configs.get_current()
            if self._config_name is None:
                raise RuntimeError("No current experiment config was previously set.")
            self._modification_date = (
                self._session.experiment_configs.get_modification_date(
                    self._config_name
                )
            )
            self._config = self._session.experiment_configs.get_current_config()

        self._updater = ConcurrentUpdater(self.update_config, 0.5)
        self._updater.start()

    def update_config(self):
        with self._session:
            new_config_name = self._session.experiment_configs.get_current()
            new_modification_date = (
                self._session.experiment_configs.get_modification_date(new_config_name)
            )
            if (self._config_name, self._modification_date) != (
                new_config_name,
                new_modification_date,
            ):
                self._config_name = new_config_name
                self._modification_date = new_modification_date
                self._config = self._session.experiment_configs.get_current_config()
                logger.info(f"Updated current experiment config to {self._config_name}")

    def get_current_config(self) -> ExperimentConfig:
        return copy.deepcopy(self._config)
