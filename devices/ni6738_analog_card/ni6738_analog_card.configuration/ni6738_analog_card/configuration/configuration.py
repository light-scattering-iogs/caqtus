from typing import Optional

from pydantic import Field, validator

from device_config import DeviceConfiguration
from device_config.channel_config import AnalogChannelConfiguration
from device_config.units_mapping import AnalogUnitsMapping
from units import Quantity


class NI6738SequencerConfiguration(DeviceConfiguration, AnalogChannelConfiguration):
    device_id: str
    time_step: float = Field(
        default=2.5e-6,
        ge=2.5e-6,
        units="s",
        description=(
            "The quantization time step used when converting step times to"
            " instructions."
        ),
    )

    @validator("channel_mappings")
    def validate_channel_mappings(cls, channel_mappings):
        channel_mappings: list[
            Optional[AnalogUnitsMapping]
        ] = super().validate_channel_mappings(channel_mappings)
        for channel, mapping in enumerate(channel_mappings):
            if mapping is not None:
                output_units = mapping.get_output_units()
                if not Quantity(1, units=output_units).is_compatible_with("V"):
                    raise ValueError(
                        f"Channel {channel} output units ({output_units}) are not"
                        " compatible with Volt"
                    )
        return channel_mappings

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def number_channels(cls) -> int:
        return 32

    def get_device_type(self) -> str:
        return "NI6738AnalogCard"

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "device_id": self.device_id,
            "time_step": self.time_step,
        }
        return super().get_device_init_args() | extra
