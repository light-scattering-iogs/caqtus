import logging
from logging.handlers import QueueHandler
from multiprocessing import Queue
from multiprocessing.managers import BaseManager
from typing import Optional

from core.control.manager import ExperimentManager
from core.session import get_standard_experiment_session_maker

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


logs_queue = Queue()
queue_handler = QueueHandler(logs_queue)
queue_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(queue_handler)

MiB = 1024 * 1024

file_handler = logging.handlers.RotatingFileHandler(
    "experiment_server.log", maxBytes=10 * MiB, backupCount=5, delay=True
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logging.getLogger().addHandler(file_handler)


def get_logs_queue():
    return logs_queue


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
    logger.info("Ready")
    m.get_server().serve_forever()
