import numpy as np

from experiment.configuration import ExperimentConfig
from experiment_control.compute_device_parameters import compute_shot_parameters
from sequence.configuration import SequenceConfig
from variable.namespace import VariableNamespace

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_compile(
    sequence_config_2: SequenceConfig,
    variables_2: VariableNamespace,
    experiment_config_2: ExperimentConfig,
):
    parameters = compute_shot_parameters(
        experiment_config_2, sequence_config_2.shot_configurations["shot"], variables_2
    )

    cam_trig = parameters["Spincore PulseBlaster sequencer"]["sequence"][12]
    logger.debug(f"{cam_trig=!r}")


    analog_clock = parameters["Spincore PulseBlaster sequencer"]["sequence"][0]
    clock_values = analog_clock.flatten().values.astype(int)

    number_rise = np.sum(np.maximum(clock_values[:-1] - clock_values[1:], 0))
    logger.debug(f"{number_rise=}")
    assert False