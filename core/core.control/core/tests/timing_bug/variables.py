from core.control.variable_namespace import VariableNamespace
from core.types.units import Quantity

variables = VariableNamespace(
    {
        "ramp_time": Quantity(80, "millisecond"),
        "mot_loading": {
            "red": {
                "power": Quantity(0, "decibel"),
                "frequency": Quantity(-3.5, "megahertz"),
            },
            "current": Quantity(2.5, "ampere"),
            "blue": {
                "power": Quantity(1.0, "dimensionless"),
                "frequency": Quantity(19, "megahertz"),
            },
            "x_current": Quantity(0.2, "ampere"),
            "y_current": Quantity(0.2, "ampere"),
            "z_current": Quantity(0.2, "ampere"),
            "time": Quantity(100, "millisecond"),
        },
        "red_mot": {
            "x_current": Quantity(0.2, "ampere"),
            "y_current": Quantity(0.08, "ampere"),
            "z_current": Quantity(0.05, "ampere"),
            "frequency": Quantity(-0.5, "megahertz"),
            "power": Quantity(-36, "decibel"),
            "current": Quantity(3, "ampere"),
        },
        "push_power": Quantity(0.5, "milliwatt"),
        "hold_time": Quantity(20, "millisecond"),
        "exposure": Quantity(50, "millisecond"),
        "imaging": {
            "x_current": Quantity(0.25, "ampere"),
            "y_current": Quantity(4.94, "ampere"),
            "z_current": Quantity(0.183, "ampere"),
            "power": Quantity(-29, "decibel"),
            "frequency": Quantity(-18, "megahertz"),
            "tweezer_power": Quantity(0.8, "dimensionless"),
        },
        "collisions": {
            "power": Quantity(-27, "decibel"),
            "frequency": Quantity(-18, "megahertz"),
        },
        "hwp_angle": Quantity(139, "dimensionless"),
        "cooling": {
            "power": Quantity(-35, "decibel"),
            "frequency": Quantity(-17.95, "megahertz"),
        },
        "rearrange": {
            "tweezer_power": Quantity(0.4, "dimensionless"),
            "time": Quantity(400, "microsecond"),
        },
        "rep": Quantity(2, "dimensionless"),
    }
)
