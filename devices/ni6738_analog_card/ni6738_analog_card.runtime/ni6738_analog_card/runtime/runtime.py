import logging
from contextlib import closing
from functools import singledispatchmethod
from typing import ClassVar

import nidaqmx
import nidaqmx.constants
import nidaqmx.system
import numpy
import numpy as np
from pydantic import Extra, Field, validator

from log_exception import log_exception
from sequencer.instructions import (
    SequencerInstruction,
    SequencerPattern,
    ChannelLabel,
    Concatenate,
    Repeat,
)
from sequencer.runtime import Sequencer, Trigger, ExternalClockOnChange, TriggerEdge

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

ns = 1e-9


class NI6738AnalogCard(Sequencer, extra=Extra.allow):
    """Device class to program the NI6738 analog card.

    Fields:
        device_id: The ID of the device to use. It is the name of the device as it appears in the NI MAX software, e.g.
        Dev1.
        time_step: The smallest allowed time step, in nanoseconds.
        external_clock: Whether to use an external clock to trigger the analog card. If False, the internal clock of the
        card is used. Otherwise, the clock is taken from the PFI0 line of the device on the rising edge. Only True is
        implemented at the moment.
    """

    channel_number: ClassVar[int] = 32

    device_id: str
    time_step: int = Field(ge=2500)
    external_clock: bool = True
    trigger: Trigger = Field(default_factory=ExternalClockOnChange)

    _task: nidaqmx.Task

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + ("run", "stop")

    @validator("external_clock")
    def _validate_external_clock(cls, external_clock: bool) -> bool:
        if not external_clock:
            raise NotImplementedError("Internal clock is not implemented")
        return external_clock

    @validator("trigger")
    def _validate_trigger(cls, trigger: Trigger) -> Trigger:
        if not isinstance(trigger, ExternalClockOnChange):
            raise NotImplementedError(
                f"Trigger type {type(trigger)} is not implemented"
            )
        if trigger.edge != TriggerEdge.RISING:
            raise NotImplementedError(
                f"Trigger edge {trigger.edge} is not implemented"
            )
        return trigger

    @log_exception(logger)
    def initialize(self) -> None:
        super().initialize()
        system = nidaqmx.system.System.local()
        if self.device_id not in system.devices:
            raise ConnectionError(f"Could not find device {self.device_id}")

        self._task = self._enter_context(closing(nidaqmx.Task()))
        self._add_closing_callback(self._task.stop)

        for ch in range(self.channel_number):
            self._task.ao_channels.add_ao_voltage_chan(
                physical_channel=f"{self.device_id}/ao{ch}",
                min_val=-10,
                max_val=+10,
                units=nidaqmx.constants.VoltageUnits.VOLTS,
            )

    @log_exception(logger)
    def update_parameters(self, *, sequence: SequencerInstruction, **kwargs) -> None:
        """Write a sequence of voltages to the analog card."""

        self._stop_task()

        values = np.concatenate(
            self._values_from_instruction(sequence), axis=1, dtype=np.float64
        )
        logger.debug(f"Writing {values.shape[1]} samples to the analog card")

        if not values.shape[0] == self.channel_number:
            raise ValueError(
                f"Expected {self.channel_number} channels, got {values.shape[0]}"
            )
        number_samples = values.shape[1]
        self._configure_timing(number_samples)

        self._write_values(values)

    def _write_values(self, values: numpy.ndarray) -> None:
        if (
            written := self._task.write(
                values,
                auto_start=False,
                timeout=0,
            )
        ) != values.shape[1]:
            raise RuntimeError(
                f"Could not write all values to the analog card, wrote {written}/{values.shape[1]}"
            )

    def _stop_task(self) -> None:
        if not self._task.is_task_done():
            self._task.wait_until_done(timeout=0)
        self._task.stop()

    def _configure_timing(self, number_of_samples: int) -> None:
        self._task.timing.cfg_samp_clk_timing(
            rate=1 / (self.time_step * ns),
            source=f"/{self.device_id}/PFI0",
            active_edge=nidaqmx.constants.Edge.RISING,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=number_of_samples,
        )

        # only take into account a trigger pulse if it is long enough to avoid
        # triggering on glitches
        self._task.timing.samp_clk_dig_fltr_min_pulse_width = self.time_step * ns / 8
        self._task.timing.samp_clk_dig_fltr_enable = True

    @log_exception(logger)
    def start_sequence(self) -> None:
        super().start_sequence()
        self._task.start()

    @log_exception(logger)
    def has_sequence_finished(self) -> bool:
        super().has_sequence_finished()
        return self._task.is_task_done()

    @singledispatchmethod
    def _values_from_instruction(
        self, instruction: SequencerInstruction
    ) -> list[np.ndarray]:
        raise NotImplementedError(f"Instruction {instruction} is not supported")

    @_values_from_instruction.register
    def _(self, pattern: SequencerPattern) -> list[np.ndarray]:
        values = pattern.values
        result = np.array(
            [values[ChannelLabel(ch)].values for ch in range(self.channel_number)]
        )
        if np.any(np.isnan(result)):
            raise ValueError(f"Pattern {pattern} contains nan")
        return [result]

    @_values_from_instruction.register
    def _(self, concatenate: Concatenate) -> list[np.ndarray]:
        result = []
        for instruction in concatenate.instructions:
            result.extend(self._values_from_instruction(instruction))
        return result

    @_values_from_instruction.register
    def _(self, repeat: Repeat) -> list[np.ndarray]:
        if len(repeat.instruction) != 1:
            raise NotImplementedError(
                "Only one instruction is supported in a repeat block at the moment"
            )
        return self._values_from_instruction(repeat.instruction.flatten())
