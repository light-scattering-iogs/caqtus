from pydantic import Field, validator

from settings_model import SettingsModel


class StaticTrapConfiguration(SettingsModel):
    """Contains the information to generate a static 1D pattern of traps.

    Fields:
        frequencies: The frequencies of each tone in Hz.
        amplitudes: The amplitudes of each tone. They have no dimension.
        phases: The phases of each tone in radian.
        sampling_rate: The sampling rate of the signal in Hz.
        number_samples: The number of samples in the waveform.
    """

    frequencies: list[float]
    amplitudes: list[float]
    phases: list[float]
    sampling_rate: float = Field(ge=0.0)
    number_samples: int = Field(ge=1)

    @property
    def number_tones(self):
        return len(self.frequencies)


class StaticTrapConfiguration2D(SettingsModel):
    config_x: StaticTrapConfiguration
    config_y: StaticTrapConfiguration

    @validator("config_y")
    def validate_config_y(cls, config_y, values):
        config_x = values["config_x"]
        if not config_y.sampling_rate == config_x.sampling_rate:
            raise ValueError(
                "The sampling rates of the two configurations must be equal."
            )
        if not config_y.number_samples == config_x.number_samples:
            raise ValueError(
                "The number of samples of the two configurations must be equal."
            )
        return config_y

    @property
    def sampling_rate(self):
        return self.config_x.sampling_rate

    @property
    def number_samples(self):
        return self.config_x.number_samples
