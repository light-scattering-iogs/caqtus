import logging

from expression import Expression
from settings_model import SettingsModel
from .lane import Lane

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class Blink(SettingsModel):
    """Indicates that the value of a digital lane should turn on and off periodically."""

    period: Expression
    phase: Expression
    duty_cycle: Expression

    def __str__(self):
        return f"Blink(T={self.period}, D={self.duty_cycle}, φ={self.phase})"


class DigitalLane(Lane[bool | Blink]):
    pass
