import logging
from multiprocessing.managers import BaseManager

from experiment_control.manager import ExperimentManager, get_logs_queue

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


if __name__ == "__main__":
    ExperimentProcessManager.register("ExperimentManager", ExperimentManager)
    ExperimentProcessManager.register("get_logs_queue", get_logs_queue)

    m = ExperimentProcessManager(address=("localhost", 60000), authkey=b"Deardear")
    m.get_server().serve_forever()
