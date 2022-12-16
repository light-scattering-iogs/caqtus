from abc import ABC, abstractmethod

import pydantic
from pydantic import Field


class SiglentSDG6000XWaveform(pydantic.BaseModel, ABC):
    class Config:
        validate_assignment = True
        validate_all = True

    @abstractmethod
    def get_scpi_basic_wave_parameters(self) -> dict[str]:
        ...


class DCVoltage(SiglentSDG6000XWaveform):
    value: float = Field(default=0, units="V", allow_mutation=False)

    def get_scpi_basic_wave_parameters(self) -> dict[str]:
        return {"WVTP": "DC", "OFST": self.value}


class SineWave(SiglentSDG6000XWaveform):
    frequency: float = Field(units="Hz", allow_mutation=False)
    amplitude: float = Field(
        units="V", description="peak-to-peak", allow_mutation=False
    )
    offset: float = Field(default=0, units="V", allow_mutation=False)
    phase: float = Field(default=0, units="deg", ge=0, le=360)

    def get_scpi_basic_wave_parameters(self) -> dict[str]:
        return {
            "WVTP": "SINE",
            "FRQ": self.frequency,
            "AMP": self.amplitude,
            "OFST": self.offset,
        }
