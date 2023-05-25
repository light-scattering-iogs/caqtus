import logging
import time
from enum import IntFlag
from functools import singledispatchmethod
from typing import ClassVar

from pydantic import Field

from device.runtime import RuntimeDevice
from log_exception import log_exception
from . import spinapi
from .instructions import Instruction, Continue, Loop, Stop

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

ns = 1e-9


class SpincoreStatus(IntFlag):
    Stopped = 2**0
    Reset = 2**1
    Running = 2**2
    Waiting = 2**3


class SpincorePulseBlaster(RuntimeDevice):
    board_number: int = 0
    spincore_lib_debug: bool = False
    core_clock: float = Field(default=100e6, units="Hz")
    instructions: list[Instruction] = []
    time_step: float = Field(ge=50e-9, units="s")

    channel_number: ClassVar[int] = 24

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + ("run",)

    @log_exception(logger)
    def initialize(self) -> None:
        super().initialize()

        spinapi.pb_set_debug(self.spincore_lib_debug)

        board_count = spinapi.pb_count_boards()
        if self.board_number >= board_count:
            raise ConnectionError(
                f"Can't access board {self.board_number}\nThere are only"
                f" {board_count} boards"
            )
        if spinapi.pb_select_board(self.board_number) != 0:
            raise ConnectionError(
                f"Can't access board {self.board_number}\n{spinapi.pb_get_error()}"
            )

        if spinapi.pb_init() != 0:
            raise ConnectionError(
                f"Can't initialize board {self.board_number}\n{spinapi.pb_get_error()}"
            )
        self._add_closing_callback(spinapi.pb_close)

        spinapi.pb_core_clock(self.core_clock / 1e6)

    @log_exception(logger)
    def update_parameters(self, /, **kwargs) -> None:
        super().update_parameters(**kwargs)

        if spinapi.pb_start_programming(spinapi.PULSE_PROGRAM) != 0:
            raise RuntimeError(
                f"Can't start programming sequence.{spinapi.pb_get_error()}"
            )

        for instruction in self.instructions:
            self._program_instruction(instruction)

        if spinapi.pb_stop_programming() != 0:
            raise RuntimeError(
                "An error occurred when finishing programming the sequence."
                f"{spinapi.pb_get_error()}"
            )

    @singledispatchmethod
    def _program_instruction(self, instruction: Instruction):
        raise NotImplementedError(f"Not implemented for {type(instruction)}")

    @_program_instruction.register
    def _(self, continue_: Continue):
        if continue_.duration < self.time_step:
            raise ValueError(
                f"The duration of the continue instruction is too short. "
                f"Minimum duration is {self.time_step} s"
            )

        # break the duration into multiple long waits and one short wait
        max_duration = 2**32 / self.core_clock
        number_of_repetitions, short_duration = divmod(continue_.duration, max_duration)
        number_of_repetitions = round(number_of_repetitions)

        flags = self._state_to_flags(continue_.values)
        logger.debug(f"{number_of_repetitions=}")
        if number_of_repetitions >= 1:
            # Delay multiplier must be greater than 2, so we divide by 2 the length of the wait and multiply the number
            # of repetitions by 2
            if (
                spinapi.pb_inst_pbonly(
                    flags,
                    spinapi.Inst.LONG_DELAY,
                    2 * number_of_repetitions,
                    max_duration / 2 / ns,
                )
                < 0
            ):
                raise RuntimeError(
                    "An error occurred when programming the sequence. "
                    f"{spinapi.pb_get_error()}"
                )
        if (
            spinapi.pb_inst_pbonly(
                flags, spinapi.Inst.CONTINUE, 0, continue_.duration / ns
            )
            < 0
        ):
            raise RuntimeError(
                "An error occurred when programming the sequence. "
                f"{spinapi.pb_get_error()}"
            )

    @_program_instruction.register
    def _(self, loop: Loop):
        if (
            loop_beginning := spinapi.pb_inst_pbonly(
                self._state_to_flags(loop.start_values),
                spinapi.Inst.LOOP,
                loop.repetitions,
                loop.start_duration / ns,
            )
        ) < 0:
            raise RuntimeError(
                "An error occurred when programming the sequence."
                f"{spinapi.pb_get_error()}"
            )

        if (
            spinapi.pb_inst_pbonly(
                self._state_to_flags(loop.end_values),
                spinapi.Inst.END_LOOP,
                loop_beginning,
                loop.end_duration / ns,
            )
            < 0
        ):
            raise RuntimeError(
                "An error occurred when programming the sequence."
                f"{spinapi.pb_get_error()}"
            )

    @_program_instruction.register
    def _(self, stop: Stop):
        flags = self._state_to_flags(stop.values)
        if (
            spinapi.pb_inst_pbonly(
                flags, spinapi.Inst.STOP, 0, 10 / self.core_clock / ns
            )
            < 0
        ):
            raise RuntimeError(
                "An error occurred when programming the sequence. "
                f"{spinapi.pb_get_error()}"
            )

    def _state_to_flags(self, states: list[bool]) -> int:
        flags = 0
        for channel, state in zip(range(self.channel_number), states):
            flags |= int(state) << channel
        return flags

    @log_exception(logger)
    def run(self):
        if spinapi.pb_reset() != 0:
            raise RuntimeError(f"Can't reset the board. {spinapi.pb_get_error()}")

        if spinapi.pb_start() != 0:
            raise RuntimeError(f"Can't start the sequence. {spinapi.pb_get_error()}")

        while spinapi.pb_read_status() & SpincoreStatus.Running:
            time.sleep(0.01)
