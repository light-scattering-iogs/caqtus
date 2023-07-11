from enum import Enum

from settings_model import SettingsModel
from .segment_name import SegmentName
from .step_name import StepName


class StepChangeCondition(Enum):
    ALWAYS = 0x0
    ON_TRIGGER = 0x40000000
    END = 0x80000000


class StepConfiguration(SettingsModel):
    segment: SegmentName
    next_step: StepName
    repetition: int
    change_condition: StepChangeCondition = StepChangeCondition.ALWAYS
