import logging
from multiprocessing.managers import BaseManager
from typing import Optional

from core.control.manager import ExperimentManager, get_logs_queue
from core.session import get_standard_experiment_session_maker

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


experiment_manager: Optional[ExperimentManager] = None


def get_experiment_manager() -> ExperimentManager:
    global experiment_manager
    if experiment_manager is None:
        experiment_manager = ExperimentManager(get_standard_experiment_session_maker())
    return experiment_manager


if __name__ == "__main__":
    ExperimentProcessManager.register(
        "connect_to_experiment_manager", get_experiment_manager
    )
    ExperimentProcessManager.register("get_logs_queue", get_logs_queue)

    m = ExperimentProcessManager(address=("localhost", 60000), authkey=b"Deardear")
    print("Ready")
    m.get_server().serve_forever()
