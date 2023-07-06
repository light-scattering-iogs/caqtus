import logging
from contextlib import closing
from typing import ClassVar

import nidaqmx
import nidaqmx.constants
import nidaqmx.system
import numpy
from pydantic import Extra, Field, validator

from device.runtime import RuntimeDevice
from log_exception import log_exception
from sequencer.time_sequence import TimeSequence

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class NI6738AnalogCard(RuntimeDevice, extra=Extra.allow):
    """Device class to program the NI6738 analog card.

    Fields:
        device_id: The ID of the device to use. It is the name of the device as it appears in the NI MAX software, e.g.
        Dev1.
        time_step: The smallest allowed time step, in seconds.
        external_clock: Whether to use an external clock to trigger the analog card. If False, the internal clock of the
        card is used. Otherwise, the clock is taken from the PFI0 line of the device on the rising edge. Only True is
        implemented at the moment.
    """

    channel_number: ClassVar[int] = 32

    device_id: str
    time_step: float = Field(ge=2.5e-6)
    external_clock: bool = True

    _task: nidaqmx.Task

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + ("run",)

    @validator("external_clock")
    def _validate_external_clock(cls, external_clock: bool) -> bool:
        if not external_clock:
            raise NotImplementedError("Internal clock is not implemented")
        return external_clock

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
    def update_parameters(self, /, sequence: TimeSequence, **kwargs) -> None:
        """Write a sequence of voltages to the analog card."""

        super().update_parameters(**kwargs)
        self._stop_task()

        pattern = sequence.unroll()
        number_samples = len(pattern)
        self._configure_timing(number_samples)

        values = numpy.empty((self.channel_number, number_samples), dtype=numpy.float64)

        for ch in range(self.channel_number):
            if numpy.any(numpy.isnan(pattern.channel_values[ch])):
                raise ValueError(f"Channel {ch} contains nan")
            values[ch, :] = pattern.channel_values[ch]

        self._write_values(values)

    def _write_values(self, values: numpy.ndarray) -> None:
        if self._task.write(
            values,
            auto_start=False,
            timeout=0,
        ) != len(values):
            raise RuntimeError("Could not write all values to the analog card")

    def _stop_task(self) -> None:
        if not self._task.is_task_done():
            self._task.wait_until_done(timeout=0)
        self._task.stop()

    def _configure_timing(self, number_of_samples: int) -> None:
        self._task.timing.cfg_samp_clk_timing(
            rate=1 / self.time_step,
            source=f"/{self.device_id}/PFI0",
            active_edge=nidaqmx.constants.Edge.RISING,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=number_of_samples,
        )

        # only take into account a trigger pulse if it is long enough to avoid
        # triggering on glitches
        self._task.timing.samp_clk_dig_fltr_min_pulse_width = self.time_step / 8
        self._task.timing.samp_clk_dig_fltr_enable = True

    @log_exception(logger)
    def run(self):
        """Starts the voltage generation task and return as soon as possible."""

        self._task.start()

    @log_exception(logger)
    def stop(self):
        self._task.wait_until_done(timeout=nidaqmx.constants.WAIT_INFINITELY)
        self._task.stop()
