import logging
from abc import ABC

import yaml

from expression import Expression
from settings_model import SettingsModel
from units import dimensionless, Quantity
from lane.configuration import Lane

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class Ramp(SettingsModel, ABC):
    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Build a ramp object from a YAML node"""
        return cls()

    @classmethod
    def representer(cls, dumper: yaml.Dumper, ramp: "Ramp"):
        """Represent a ramp object with a yaml string with no value"""

        return dumper.represent_scalar(f"!{cls.__name__}", "")


class LinearRamp(Ramp):
    pass


class AnalogLane(Lane[Expression | Ramp]):
    units: str

    def has_dimension(self) -> bool:
        return not Quantity(1, units=self.units).is_compatible_with(dimensionless)
