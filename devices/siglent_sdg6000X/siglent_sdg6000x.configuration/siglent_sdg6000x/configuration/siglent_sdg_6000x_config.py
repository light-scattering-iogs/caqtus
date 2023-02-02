from abc import ABC
from typing import ClassVar, Literal, Optional

from pydantic import Field

from device_config import DeviceConfiguration
from expression import Expression
from sequence import VariableDeclaration
from settings_model import SettingsModel


class SiglentSDG6000XModulationConfiguration(SettingsModel, ABC):
    source: Literal["INT", "EXT", "CH1", "CH2"] = "EXT"


class AmplitudeModulationConfiguration(SiglentSDG6000XModulationConfiguration):
    depth: float = Field(default=100, units="%")


class FrequencyModulationConfiguration(SiglentSDG6000XModulationConfiguration):
    deviation: float = Field(ge=0, units="Hz")


class SineWaveConfiguration(SettingsModel):
    frequency: VariableDeclaration = VariableDeclaration("", Expression("..."))
    amplitude: VariableDeclaration = VariableDeclaration("", Expression("..."))
    offset: VariableDeclaration = VariableDeclaration("", Expression("..."))
    phase: VariableDeclaration = VariableDeclaration("", Expression("..."))


class SiglentSDG6000XChannelConfiguration(SettingsModel):
    output_enabled: bool = False
    output_load: float | Literal["HZ"] = Field(default=50, ge=50, units="Ohm")
    polarity: Literal["NOR", "INVT"] = Field(default="NOR")
    waveform: SineWaveConfiguration = Field(default_factory=SineWaveConfiguration)
    modulation: Optional[SiglentSDG6000XModulationConfiguration] = None


class SiglentSDG6000XConfiguration(DeviceConfiguration):
    channel_number: ClassVar[int] = 2

    visa_resource: str = ""
    channel_configurations: list[SiglentSDG6000XChannelConfiguration] = Field(
        default_factory=lambda: [
            SiglentSDG6000XChannelConfiguration()
            for _ in range(SiglentSDG6000XConfiguration.channel_number)
        ]
    )

    def get_device_type(self) -> str:
        return "SiglentSDG6000XWaveformGenerator"
