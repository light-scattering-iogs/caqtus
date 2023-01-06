import logging
from typing import ClassVar

import nidaqmx
import nidaqmx.constants
import nidaqmx.system
import numpy
from device import RuntimeDevice
from pydantic import Extra, Field, validator

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class NI6738AnalogCard(RuntimeDevice, extra=Extra.allow):
    device_id: str
    time_step: float = Field(ge=2.5e-6, units="s")
    values: numpy.ndarray = Field(
        default_factory=lambda: numpy.array([0]),
        units="V",
        description=(
            "Voltages for each channel with shape (channel_number, samples_per_channel)"
        ),
    )

    channel_number: ClassVar[int] = 32
    _task: nidaqmx.Task

    @validator("values")
    def validate_values(cls, analog_voltages):
        if numpy.any(numpy.isnan(analog_voltages)):
            raise ValueError(f"Analog voltages can't be nan")
        return analog_voltages

    def start(self) -> None:
        super().start()
        system = nidaqmx.system.System.local()
        if self.device_id not in system.devices:
            raise ConnectionError(f"Could not find device {self.device_id}")

        self._task = nidaqmx.Task()

        for ch in range(self.channel_number):
            self._task.ao_channels.add_ao_voltage_chan(
                physical_channel=f"{self.device_id}/ao{ch}",
                min_val=-10,
                max_val=+10,
                units=nidaqmx.constants.VoltageUnits.VOLTS,
            )

    def update_parameters(self, /, **kwargs) -> None:
        super().update_parameters(**kwargs)
        self._task.stop()
        self._task.timing.cfg_samp_clk_timing(
            rate=1 / self.time_step,
            source=f"/{self.device_id}/PFI0",
            active_edge=nidaqmx.constants.Edge.RISING,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.values.shape[1],
        )
        values = self.values.astype(numpy.float64)
        if numpy.any(numpy.isnan(values)):
            raise ValueError(f"Analog voltages can't be nan")

        self._task.write(
            values,
            auto_start=False,
            timeout=nidaqmx.constants.WAIT_INFINITELY,
        )

        # only take into account a trigger pulse if it is long enough to avoid
        # triggering on glitches
        self._task.timing.samp_clk_dig_fltr_min_pulse_width = self.time_step / 8
        self._task.timing.samp_clk_dig_fltr_enable = True

    def run(self):
        self._task.start()

    def shutdown(self):
        # noinspection PyBroadException
        try:
            self._task.stop()
            self._task.close()
        except Exception as err:
            raise err
        finally:
            super().shutdown()
