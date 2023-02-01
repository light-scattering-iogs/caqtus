from typing import ClassVar

from pydantic import Field

from device_config import DeviceConfiguration
from expression import Expression
from sequence import VariableDeclaration
from settings_model import SettingsModel


class SineWaveConfiguration(SettingsModel):
    frequency: VariableDeclaration = VariableDeclaration("", Expression("..."))
    amplitude: VariableDeclaration = VariableDeclaration("", Expression("..."))
    offset: VariableDeclaration = VariableDeclaration("", Expression("..."))
    phase: VariableDeclaration = VariableDeclaration("", Expression("..."))


class SiglentSDG6000XConfiguration(DeviceConfiguration):
    channel_number: ClassVar[int] = 2

    def get_device_type(self) -> str:
        return "SiglentSDG6000XWaveformGenerator"

    waveform_configs: list[SineWaveConfiguration] = Field(
        default_factory=lambda: [
            SineWaveConfiguration()
            for _ in range(SiglentSDG6000XConfiguration.channel_number)
        ]
    )
