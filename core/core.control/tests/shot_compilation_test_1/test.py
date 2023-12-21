from pathlib import Path

from core.configuration import ExperimentConfig
from core.configuration.sequence import ShotConfiguration
from core.control.compute_device_parameters import compute_shot_parameters
from sequencer.instructions.instructions import to_flat_dict
from util import serialization
from .variables import variables


def test():
    experiment_config_file = Path(__file__).parent / "experiment_config.json"
    with open(experiment_config_file, "r") as file:
        experiment_config = serialization.from_json(file.read(), ExperimentConfig)

    shot_config_file = Path(__file__).parent / "shot_config.yaml"
    with open(shot_config_file, "r") as file:
        shot_config = ShotConfiguration.from_yaml(file.read())

    result = compute_shot_parameters(
        experiment_config,
        shot_config,
        variables,
    )
    print(to_flat_dict(result["Spincore PulseBlaster sequencer"]["sequence"]))
    # with open("swabian_result.pkl", "rb") as file:
    #     pickle.dump(to_flat_dict(result["Swabian pulse streamer"]["sequence"]), file)
