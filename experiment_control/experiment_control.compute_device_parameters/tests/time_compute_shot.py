import logging
import time

from experiment.configuration import ExperimentConfig
from experiment_control.compute_device_parameters import compute_shot_parameters
from sequence.configuration import SequenceConfig
from variable.namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_compile(
    sequence_config_2: SequenceConfig,
    variables_2: VariableNamespace,
    experiment_config_2: ExperimentConfig,
):
    n = 10
    t0 = time.perf_counter()
    for _ in range(n):
        compute_shot_parameters(
            experiment_config_2,
            sequence_config_2.shot_configurations["shot"],
            variables_2,
        )
    t1 = time.perf_counter()

    logger.info(f"Duration: {(t1 - t0) / n}")
    assert False
