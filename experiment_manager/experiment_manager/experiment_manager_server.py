import logging
from multiprocessing.managers import BaseManager

from experiment_manager import ExperimentManager

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


ExperimentProcessManager.register("ExperimentManager", ExperimentManager)

if __name__ == "__main__":
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel("DEBUG")
    m = ExperimentProcessManager(address=("localhost", 50000), authkey=b"Deardear")
    s = m.get_server()
    logger.info("Start experiment manager server")
    s.serve_forever()
