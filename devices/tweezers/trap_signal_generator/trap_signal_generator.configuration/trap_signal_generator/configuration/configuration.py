from pydantic import Field

from settings_model import SettingsModel


class StaticTrapConfiguration(SettingsModel):
    frequencies: list[float] = Field(units="Hz")
    amplitudes: list[float] = Field(units="V")
    phases: list[float] = Field(units="rad")
    sampling_rate: float = Field(units="Hz")
    number_samples: int = Field()

    @property
    def number_tones(self):
        return len(self.frequencies)
