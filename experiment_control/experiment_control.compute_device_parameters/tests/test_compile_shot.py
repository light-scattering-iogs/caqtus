from experiment.configuration import ExperimentConfig
from experiment_control.compute_device_parameters import compute_shot_parameters
from sequence.configuration import SequenceConfig
from variable.namespace import VariableNamespace


def test_compile(
    sequence_config_2: SequenceConfig,
    variables_2: VariableNamespace,
    experiment_config_2: ExperimentConfig,
):
    parameters = compute_shot_parameters(
        experiment_config_2, sequence_config_2.shot_configurations["shot"], variables_2
    )
