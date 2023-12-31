import copy
import logging

from core.session import ExperimentConfig, ExperimentSessionMaker
from util.concurrent import BackgroundScheduler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CurrentExperimentConfigWatcher:
    def __init__(self, session_maker: ExperimentSessionMaker):
        self._session = session_maker()
        # with self._session:
        #     self._config_name = self._session.experiment_configs.get_current_by_name()
        #     if self._config_name is None:
        #         raise RuntimeError("No current experiment config was previously set.")
        #     self._modification_date = (
        #         self._session.experiment_configs.get_modification_date(
        #             self._config_name
        #         )
        #     )
        #     self._config = self._session.experiment_configs.get_current_config()
        #
        self._updater = BackgroundScheduler(max_workers=1)

    def __enter__(self):
        self._updater.__enter__()
        # self._updater.schedule_task(self.update_config, 0.5)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._updater.__exit__(exc_type, exc_value, traceback)

    def update_config(self):
        with self._session:
            new_config_name = self._session.experiment_configs.get_current_by_name()
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
