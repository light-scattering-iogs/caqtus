import logging

from experiment_control.compute_device_parameters.clock_instruction import (
    ClockInstruction,
)
from experiment_control.compute_device_parameters.compile_lane import (
    compile_clock_instruction,
    number_ticks,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_clock_compilation():
    clock_time_step = 2500
    source_time_step = 50
    clock_requirement = [
        ClockInstruction(
            start=0.0,
            stop=10e-3,
            order=ClockInstruction.StepInstruction.TriggerStart,
            time_step=clock_time_step,
        ),
        ClockInstruction(
            start=10e-3,
            stop=90e-3,
            order=ClockInstruction.StepInstruction.Clock,
            time_step=clock_time_step,
        ),
        ClockInstruction(
            start=90e-3,
            stop=240e-3,
            order=ClockInstruction.StepInstruction.TriggerStart,
            time_step=clock_time_step,
        ),
    ]

    logger.debug(f"{divmod(clock_time_step, source_time_step)=}")

    instruction = compile_clock_instruction(clock_requirement, source_time_step)
    logger.debug(f"{instruction=}")
    assert len(instruction) == number_ticks(0.0, 240e-3, source_time_step)
