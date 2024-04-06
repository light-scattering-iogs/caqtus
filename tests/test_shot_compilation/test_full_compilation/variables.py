from caqtus.shot_compilation import VariableNamespace
from caqtus.types.units import Quantity

variables = VariableNamespace(
    {
        "mot_loading": {
            "duration": Quantity(100, "millisecond"),
            "current": Quantity(1.186, "ampere"),
            "x_current": Quantity(0.135, "ampere"),
            "y_current": Quantity(0.381, "ampere"),
            "z_current": Quantity(-0.119, "ampere"),
            "blue_power": 1.0,
            "blue_frequency": Quantity(18.983, "megahertz"),
            "red_frequency": Quantity(-2.712, "megahertz"),
            "red_power": Quantity(0, "decibel"),
            "push_power": Quantity(0.7, "milliwatt"),
        },
        "imaging": {
            "power": Quantity(-29, "decibel"),
            "frequency": Quantity(-18.076, "megahertz"),
            "exposure": Quantity(30, "millisecond"),
            "x_current": Quantity(0.25, "ampere"),
            "y_current": Quantity(4.94, "ampere"),
            "z_current": Quantity(0.183, "ampere"),
        },
        "red_mot": {
            "ramp_duration": Quantity(130, "millisecond"),
            "x_current": Quantity(0.27, "ampere"),
            "x_current_1": Quantity(0.26, "ampere"),
            "x_current_2": Quantity(0.31, "ampere"),
            "y_current": Quantity(0.092, "ampere"),
            "z_current": Quantity(0.018, "ampere"),
            "current": Quantity(0.8, "ampere"),
            "power": Quantity(-36, "decibel"),
            "frequency": Quantity(-1, "megahertz"),
            "duration": Quantity(80, "millisecond"),
        },
        "collisions": {
            "power": Quantity(-21, "decibel"),
            "frequency": Quantity(-18.08, "megahertz"),
            "duration": Quantity(30, "millisecond"),
        },
        "tweezers": {
            "loading_power": 0.45,
            "imaging_power": 0.42,
            "hwp_angle": Quantity(139.75, "degree"),
            "rearrangement_duration": Quantity(450, "microsecond"),
            "move_time": Quantity(600, "microsecond"),
        },
        "probe": {
            "frequency": Quantity(-18.315, "megahertz"),
            "power": Quantity(-23, "decibel"),
        },
        "repump": {
            "frequency": Quantity(-16.65, "megahertz"),
            "duration": Quantity(25, "millisecond"),
        },
        "cooling": {"frequency": Quantity(-18.01, "megahertz")},
        "target_fringe_position": 0.7,
        "kill_frequency": Quantity(40, "megahertz"),
        "kill_power": 1.0,
        "kill_time": Quantity(150, "nanosecond"),
        "kill_current": Quantity(4.96, "ampere"),
        "red_duration": Quantity(7, "microsecond"),
        "spacing": Quantity(3.0, "micrometer"),
        "rep": 0.0,
    }
)
