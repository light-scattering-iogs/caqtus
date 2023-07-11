from settings_model import SettingsModel
from spectum_awg_m4i66xx_x8.runtime import (
    StepName,
    StepConfiguration,
    SegmentName,
    SegmentData,
)
from trap_signal_generator.configuration import StaticTrapConfiguration2D


class MoveConfiguration(SettingsModel):
    """

    Fields:
        initial_config: The initial configuration of the trap.
        final_config: The final configuration of the trap.
        move_duration: The time to move from the initial to the final configuration, in seconds.
        scale_x: The scale factor for the x-axis, in Volt.
        scale_y: The scale factor for the y-axis, in Volt.
    """

    initial_config: StaticTrapConfiguration2D
    final_config: StaticTrapConfiguration2D
    move_duration: float


def generate_move(
    move_config: MoveConfiguration,
) -> tuple[dict[StepName, StepConfiguration], dict[SegmentName, SegmentData]]:
    pass
