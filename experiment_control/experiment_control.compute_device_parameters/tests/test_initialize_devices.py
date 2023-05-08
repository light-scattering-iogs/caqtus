from pprint import pprint

from experiment_config import ExperimentConfig
from sequence import SequenceConfig

from experiment_manager.initialize_devices import get_devices_initialization_parameters

experiment_config_path = (
    "C:\\Users\\Damien Bloch\\AppData\\Local\\Caqtus\\ExperimentControl\\config.yaml"
)
sequence_config_path = (
    "C:\\Users\\Damien"
    " Bloch\\AppData\\Local\\Caqtus\\ExperimentControl\\data\\test\\sequence_config.yaml"
)

with open(experiment_config_path) as file:
    experiment_config = ExperimentConfig.from_yaml(file.read())

with open(sequence_config_path) as file:
    sequence_config = SequenceConfig.from_yaml(file.read())

pprint(
    get_devices_initialization_parameters(experiment_config, sequence_config),
    sort_dicts=False,
    compact=True,
)
