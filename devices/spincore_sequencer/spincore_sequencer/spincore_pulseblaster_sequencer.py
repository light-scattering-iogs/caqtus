import logging
import time
from enum import IntFlag
from functools import singledispatchmethod
from typing import ClassVar

from device import Device
from pydantic import Field

from . import spinapi
from .instructions import Instruction, Continue, Loop, Stop

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SpincoreStatus(IntFlag):
    Stopped = 2 ** 0
    Reset = 2 ** 1
    Running = 2 ** 2
    Waiting = 2 ** 3


class SpincorePulseBlaster(Device):
    board_number: int = 0
    spincore_lib_debug: bool = False
    core_clock: float = Field(default=100e6, units="Hz")
    instructions: list[Instruction] = []
    time_step: float = Field(ge=50e-9, units="s")

    channel_number: ClassVar[int] = 24

    def start(self) -> None:
        super().start()

        spinapi.pb_set_debug(self.spincore_lib_debug)

        board_count = spinapi.pb_count_boards()
        if self.board_number >= board_count:
            raise ConnectionError(
                f"Can't access board {self.board_number}\nThere are only {board_count} boards"
            )
        if spinapi.pb_select_board(self.board_number) != 0:
            raise ConnectionError(
                f"Can't access board {self.board_number}\n{spinapi.pb_get_error()}"
            )

        if spinapi.pb_init() != 0:
            raise ConnectionError(
                f"Can't initialize board {self.board_number}\n{spinapi.pb_get_error()}"
            )

        spinapi.pb_core_clock(self.core_clock / 1e6)

    def apply_rt_variables(self, /, **kwargs) -> None:
        super().apply_rt_variables(**kwargs)

        if spinapi.pb_start_programming(spinapi.PULSE_PROGRAM) != 0:
            raise RuntimeError(
                f"Can't start programming sequence." f"{spinapi.pb_get_error()}"
            )

        for instruction in self.instructions:
            self._program_instruction(instruction)

        if spinapi.pb_stop_programming() != 0:
            raise RuntimeError(
                f"An error occurred when finishing programming the sequence."
                f"{spinapi.pb_get_error()}"
            )

    @singledispatchmethod
    def _program_instruction(self, instruction: Instruction):
        raise NotImplementedError(f"Not implemented for {type(instruction)}")

    @_program_instruction.register
    def _(self, continue_: Continue):
        flags = self._state_to_flags(continue_.values)
        if (
                spinapi.pb_inst_pbonly(
                    flags, spinapi.Inst.CONTINUE, 0, continue_.duration * 1e9
                )
                < 0
        ):
            raise RuntimeError(
                f"An error occurred when programming the sequence. "
                f"{spinapi.pb_get_error()}"
            )

    @_program_instruction.register
    def _(self, loop: Loop):
        if (
                loop_beginning := spinapi.pb_inst_pbonly(
                    self._state_to_flags(loop.start_values),
                    spinapi.Inst.LOOP,
                    loop.repetitions,
                    loop.start_duration * 1e9,
                )
        ) < 0:
            raise RuntimeError(
                f"An error occurred when programming the sequence."
                f"{spinapi.pb_get_error()}"
            )

        if (
                spinapi.pb_inst_pbonly(
                    self._state_to_flags(loop.end_values),
                    spinapi.Inst.END_LOOP,
                    loop_beginning,
                    loop.end_duration * 1e9,
                )
                < 0
        ):
            raise RuntimeError(
                f"An error occurred when programming the sequence."
                f"{spinapi.pb_get_error()}"
            )

    @_program_instruction.register
    def _(self, stop: Stop):
        flags = self._state_to_flags(stop.values)
        if (
                spinapi.pb_inst_pbonly(
                    flags, spinapi.Inst.STOP, 0, 10 / self.core_clock * 1e9
                )
                < 0
        ):
            raise RuntimeError(
                f"An error occurred when programming the sequence. "
                f"{spinapi.pb_get_error()}"
            )

    def _state_to_flags(self, states: list[bool]) -> int:
        flags = 0
        for channel, state in zip(range(self.channel_number), states):
            flags |= int(state) << channel
        return flags

    def run(self):
        if spinapi.pb_reset() != 0:
            raise RuntimeError(f"Can't reset the board. {spinapi.pb_get_error()}")

        if spinapi.pb_start() != 0:
            raise RuntimeError(f"Can't start the sequence. {spinapi.pb_get_error()}")

        while (status := spinapi.pb_read_status()) & SpincoreStatus.Running:
            time.sleep(0.01)

    def shutdown(self):
        error_msg = None
        try:
            if spinapi.pb_close() != 0:
                error_msg = spinapi.pb_get_error()
        finally:
            super().shutdown()

        if error_msg is not None:
            raise ConnectionError(
                f"An error occurred when closing board {self.board_number}: {error_msg}"
            )
