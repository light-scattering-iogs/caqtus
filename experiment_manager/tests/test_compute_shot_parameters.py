import timeit
from pprint import pprint

import units
from experiment_config import ExperimentConfig
from experiment_manager.compute_shot_parameters import compute_shot_parameters
from sequence import SequenceConfig

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

variables = {
    "ramp_time": units.Quantity(150, "ms"),
    "collision_time": units.Quantity(200, "ms"),
    "turn_time": units.Quantity(10, "ms"),
    "hold_time": units.Quantity(20, "ms"),
    "exposure": units.Quantity(40, "ms"),
    "mot_loading_current": units.Quantity(3, "A"),
    "red_mot_current": units.Quantity(1, "A"),
    "mot_loading_x_current": units.Quantity(0.1, "A"),
    "mot_loading_y_current": units.Quantity(0.1, "A"),
    "mot_loading_z_current": units.Quantity(0.1, "A"),
    "red_mot_x_current": units.Quantity(0.1, "A"),
    "red_mot_y_current": units.Quantity(0.1, "A"),
    "red_mot_z_current": units.Quantity(0.1, "A"),
    "b_field": units.Quantity(0.5, "A"),
    "mot_loading_blue_power": units.Quantity(0.1),
    "mot_loading_red_power": units.Quantity(0.1),
    "red_mot_power": units.Quantity(0.1),
    "collision_red_power": units.Quantity(0.1),
    "cooling_red_power": units.Quantity(0.1),
    "imaging_red_power": units.Quantity(0.1),
    "mot_loading_red_detuning": units.Quantity(-3, "MHz"),
    "red_mot_detuning": units.Quantity(-1.5, "MHz"),
    "collision_red_detuning": units.Quantity(-1., "MHz"),
    "cooling_red_detuning": units.Quantity(-0.1, "MHz"),
    "imaging_red_detuning": units.Quantity(-0., "MHz"),
    "trap_power": units.Quantity(0.7),
    "collision_trap_power": units.Quantity(0.1),
    "imaging_trap_power": units.Quantity(0.1),
}

duration = timeit.timeit(
    lambda: compute_shot_parameters(
        experiment_config, sequence_config.shot_configurations["shot"], variables
    ),
    number=10,
) / 10


pprint(
    compute_shot_parameters(
        experiment_config, sequence_config.shot_configurations["shot"], variables
    )["Spincore PulseBlaster sequencer"]["instructions"],
    sort_dicts=False,
    compact=True,
)

print(f"duration={duration*1e3:.1f} ms")
