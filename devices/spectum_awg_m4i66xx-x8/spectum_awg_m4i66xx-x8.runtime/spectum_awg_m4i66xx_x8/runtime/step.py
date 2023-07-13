from enum import Enum
from typing import NewType

from settings_model import SettingsModel
from .segment import SegmentName

StepName = NewType("StepName", str)


class StepChangeCondition(Enum):
    ALWAYS = 0x0
    ON_TRIGGER = 0x40000000
    END = 0x80000000


class StepConfiguration(SettingsModel):
    segment: SegmentName
    next_step: StepName
    repetition: int
    change_condition: StepChangeCondition = StepChangeCondition.ALWAYS
