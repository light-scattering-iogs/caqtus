import logging
from typing import ClassVar, Literal, Optional

import pyvisa
import pyvisa.resources
from pydantic import Field, validator
from pyvisa.constants import AccessModes

from settings_model import SettingsModel
from device import RuntimeDevice
from modulation import SiglentSDG6000XModulation
from waveforms import SiglentSDG6000XWaveform, DCVoltage

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SiglentSDG6000XChannel(SettingsModel):
    output_enabled: bool = Field(allow_mutation=False)
    output_load: float | Literal["HZ"] = Field(
        default=50, ge=50, units="Ohm", allow_mutation=False
    )
    polarity: Literal["NOR", "INVT"] = Field(default="NOR", allow_mutation=False)
    waveform: SiglentSDG6000XWaveform = Field(default_factory=DCVoltage)
    modulation: Optional[SiglentSDG6000XModulation] = Field(
        default=None, allow_mutation=False
    )


class SiglentSDG6000XWaveformGenerator(RuntimeDevice):
    """RuntimeDevice class to control the Siglent waveform generator SDG6000X series"""

    channel_number: ClassVar[int] = 2
    channel_names: ClassVar[list[str]] = [f"C{i + 1}" for i in range(channel_number)]

    visa_resource_name: str = Field(allow_mutation=False)
    timeout: float = Field(
        default=1,
        units="s",
        description="Maximum amount of time to wait for an answer from the device before raising an error",
        allow_mutation=False,
    )
    channel_configurations: tuple[SiglentSDG6000XChannel, ...] = Field()

    @validator("channel_configurations")
    def validate_channel_configurations(cls, channel_configurations):
        if len(channel_configurations) != cls.channel_number:
            raise ValueError(
                "Number of channel configurations doesn't match number of device channels"
            )
        return channel_configurations

    _device: pyvisa.resources.MessageBasedResource

    @staticmethod
    def list_all_visa_resources():
        resource_manager = pyvisa.ResourceManager()
        return resource_manager.list_resources()

    def start(self) -> None:
        super().start()

        resource_manager = pyvisa.ResourceManager()

        # noinspection PyTypeChecker
        self._device = resource_manager.open_resource(
            resource_name=self.visa_resource_name,
            resource_pyclass=pyvisa.resources.MessageBasedResource,
            access_mode=AccessModes.exclusive_lock,
            timeout=int(self.timeout * 1e3),
        )

        self._setup()

    def update_parameters(self, /, **kwargs) -> None:
        super().update_parameters(**kwargs)
        self._setup()

    def _setup(self):
        self._shutdown_outputs()
        self._setup_waveforms()
        self._setup_modulations()
        self._setup_outputs()

    def shutdown(self):
        try:
            self._device.close()
        except Exception as error:
            raise error
        finally:
            super().shutdown()

    def get_identity(self) -> str:
        return self._device.query("*IDN?")

    def _shutdown_outputs(self):
        for channel in range(self.channel_number):
            self._shutdown_channel_output(channel)

    def _shutdown_channel_output(self, channel: int):
        channel_name = self.channel_names[channel]
        message = f"{channel_name}:OUTPUT OFF"
        self._device.write(message)

    def _setup_waveforms(self):
        for channel, channel_configuration in enumerate(self.channel_configurations):
            self._setup_channel_waveform(channel, channel_configuration.waveform)

    def _setup_channel_waveform(self, channel: int, waveform: SiglentSDG6000XWaveform):
        channel_name = self.channel_names[channel]
        for parameter, value in waveform.get_scpi_basic_wave_parameters().items():
            message = f"{channel_name}:BASIC_WAVE {parameter},{value}"
            self._device.write(message)

    def _setup_modulations(self):
        for channel, channel_configuration in enumerate(self.channel_configurations):
            self._setup_channel_modulation(channel, channel_configuration.modulation)

    def _setup_channel_modulation(
        self, channel: int, modulation: Optional[SiglentSDG6000XModulation]
    ):
        channel_name = self.channel_names[channel]
        if modulation is None:
            message = f"{channel_name}:MODULATEWAVE STATE,OFF"
            self._device.write(message)
        else:
            message = f"{channel_name}:MODULATEWAVE STATE,ON"
            self._device.write(message)

            message = f"{channel_name}:MODULATEWAVE {modulation.get_modulation_type()}"
            self._device.write(message)

            for parameter, value in modulation.get_modulation_parameters():
                message = f"{channel_name}:MODULATEWAVE {parameter},{value}"
                self._device.write(message)

    def _setup_outputs(self):
        for channel, channel_configuration in enumerate(self.channel_configurations):
            self._setup_channel_output(channel, channel_configuration)

    def _setup_channel_output(self, channel: int, config: SiglentSDG6000XChannel):
        channel_name = self.channel_names[channel]
        state = "ON" if config.output_enabled else "OFF"
        message = (
            f"{channel_name}:"
            f"OUTPUT {state},"
            f"LOAD,{config.output_load},"
            f"PLRT,{config.polarity}"
        )
        self._device.write(message)
