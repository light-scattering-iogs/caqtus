from abc import ABC, abstractmethod

from pydantic import Field

from common.settings_model.settings_model import SettingsModel


class SiglentSDG6000XWaveform(SettingsModel, ABC):
    @abstractmethod
    def get_scpi_basic_wave_parameters(self) -> dict[str]:
        ...


class DCVoltage(SiglentSDG6000XWaveform):
    value: float = Field(default=0, units="V")

    def get_scpi_basic_wave_parameters(self) -> dict[str]:
        return {"WVTP": "DC", "OFST": self.value}


class SineWave(SiglentSDG6000XWaveform):
    frequency: float = Field(units="Hz")
    amplitude: float = Field(
        units="V", description="peak-to-peak amplitude of the waveform"
    )
    offset: float = Field(default=0, units="V")
    phase: float = Field(default=0, units="deg", ge=0, le=360)

    def get_scpi_basic_wave_parameters(self) -> dict[str]:
        return {
            "WVTP": "SINE",
            "FRQ": self.frequency,
            "AMP": self.amplitude,
            "OFST": self.offset,
        }
