import logging
from contextlib import closing
from functools import singledispatchmethod
from typing import ClassVar

import attrs
import nidaqmx
import nidaqmx.constants
import nidaqmx.errors
import nidaqmx.system
import numpy
import numpy as np
from attrs.setters import frozen
from attrs.validators import instance_of, ge

from caqtus.device import RuntimeDevice
from caqtus.device.sequencer import (
    Sequencer,
    Trigger,
    ExternalClockOnChange,
    TriggerEdge,
)
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Pattern,
    Concatenated,
    Repeated,
)
from caqtus.utils import log_exception

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

ns = 1e-9


def wrap_nidaqmx_error(f):
    def wrapper(*args, **kwargs):
        error = None
        try:
            return f(*args, **kwargs)
        except nidaqmx.errors.DaqError as e:
            error = RuntimeError(str(e))
        if error:
            raise error

    return wrapper


@attrs.define(slots=False)
class NI6738AnalogCard(Sequencer, RuntimeDevice):
    """Device class to program the NI6738 analog card.

    Fields:
        device_id: The ID of the device to use.
        It is the name of the device as it appears in the NI MAX software, e.g. Dev0.
        time_step: The smallest allowed time step, in nanoseconds.
        trigger: Indicates how the sequence is started and how it is clocked.
    """

    channel_number: ClassVar[int] = 32

    time_step: int = attrs.field(
        validator=[instance_of(int), ge(2500)], on_setattr=frozen
    )
    device_id: str = attrs.field(validator=instance_of(str), on_setattr=frozen)
    trigger: Trigger = attrs.field(validator=instance_of(Trigger), on_setattr=frozen)

    _task: nidaqmx.Task = attrs.field(init=False)

    @trigger.validator  # type: ignore
    def _validate_trigger(self, _, value):
        if not isinstance(value, ExternalClockOnChange):
            raise NotImplementedError(f"Trigger type {type(value)} is not implemented")
        if value.edge != TriggerEdge.RISING:
            raise NotImplementedError(f"Trigger edge {value.edge} is not implemented")

    @log_exception(logger)
    @wrap_nidaqmx_error
    def initialize(self) -> None:
        super().initialize()
        system = nidaqmx.system.System.local()
        if self.device_id not in system.devices:
            raise ConnectionError(f"Could not find device {self.device_id}")

        self._task = self._enter_context(closing(nidaqmx.Task()))
        self._add_closing_callback(wrap_nidaqmx_error(self._task.stop))

        for ch in range(self.channel_number):
            self._task.ao_channels.add_ao_voltage_chan(
                physical_channel=f"{self.device_id}/ao{ch}",
                min_val=-10,
                max_val=+10,
                units=nidaqmx.constants.VoltageUnits.VOLTS,
            )

    @log_exception(logger)
    @wrap_nidaqmx_error
    def update_parameters(self, sequence: SequencerInstruction) -> None:
        """Write a sequence of voltages to the analog card."""

        self._stop_task()

        self._program_sequence(sequence)

        self._set_sequence_programmed()

    def _program_sequence(self, sequence: SequencerInstruction) -> None:
        logger.debug("Programmed ni6738")
        values = np.concatenate(
            self._values_from_instruction(sequence), axis=1, dtype=np.float64
        )

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
    @wrap_nidaqmx_error
    def start_sequence(self) -> None:
        super().start_sequence()
        self._task.start()

    @log_exception(logger)
    @wrap_nidaqmx_error
    def has_sequence_finished(self) -> bool:
        super().has_sequence_finished()
        return self._task.is_task_done()

    @singledispatchmethod
    def _values_from_instruction(
        self, instruction: SequencerInstruction
    ) -> list[np.ndarray]:
        raise NotImplementedError(f"Instruction {instruction} is not supported")

    @_values_from_instruction.register
    def _(self, pattern: Pattern) -> list[np.ndarray]:
        values = pattern.array
        result = np.array([values[f"ch {ch}"] for ch in range(self.channel_number)])
        if np.any(np.isnan(result)):
            raise ValueError(f"Pattern {pattern} contains nan")
        return [result]

    @_values_from_instruction.register
    def _(self, concatenate: Concatenated) -> list[np.ndarray]:
        result = []
        for instruction in concatenate.instructions:
            result.extend(self._values_from_instruction(instruction))
        return result

    @_values_from_instruction.register
    def _(self, repeat: Repeated) -> list[np.ndarray]:
        if len(repeat.instruction) != 1:
            raise NotImplementedError(
                "Only one instruction is supported in a repeat block at the moment"
            )
        return self._values_from_instruction(repeat.instruction.to_pattern())
