import pickle
import time
from pathlib import Path

from core.configuration import ExperimentConfig
from core.configuration.sequence import ShotConfiguration
from core.control.compute_device_parameters import compute_shot_parameters
from util import serialization
from .variables import variables


def test():
    experiment_config_file = Path(__file__).parent / "experiment_config.json"
    with open(experiment_config_file, "r") as file:
        experiment_config = serialization.from_json(file.read(), ExperimentConfig)

    shot_config_file = Path(__file__).parent / "shot_config.yaml"
    with open(shot_config_file, "r") as file:
        shot_config = ShotConfiguration.from_yaml(file.read())
    t0 = time.time()
    result = compute_shot_parameters(
        experiment_config,
        shot_config,
        variables,
    )
    t1 = time.time()
    print(f"Time: {t1-t0}")
    with open("result.pkl", "rb") as file:
        reference = pickle.load(file)
    for sequencer in ["Spincore PulseBlaster sequencer", "NI6738 card"]:
        assert (
            result[sequencer]["sequence"].to_pattern()
            == reference[sequencer]["sequence"].to_pattern()
        )
