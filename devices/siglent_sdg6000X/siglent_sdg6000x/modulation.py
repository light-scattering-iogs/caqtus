from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field, validator


class SiglentSDG6000XModulation(BaseModel, ABC):
    source: Literal["INT", "EXT", "CH1", "CH2"] = Field(
        default="EXT", allow_mutation=False
    )

    @validator("source")
    def validate_source(cls, source):
        if source == "INT":
            raise NotImplementedError("Internal modulation source is not implemented")
        return source

    @abstractmethod
    def get_modulation_type(self) -> str:
        ...

    @abstractmethod
    def get_modulation_parameters(self) -> dict[str]:
        ...

    class Config:
        validate_assignment = True
        validate_all = True


class AmplitudeModulation(SiglentSDG6000XModulation):
    depth: float = Field(default=100, units="%", allow_mutation=False)
    def get_modulation_type(self) -> str:
        return "AM"

    def get_modulation_parameters(self) -> dict[str]:
        return {"AM,SRC": self.source, "AM,DEPTHI": self.depth}


class FrequencyModulation(SiglentSDG6000XModulation):
    deviation: float = Field(ge=0, units="Hz", allow_mutation=False)

    def get_modulation_type(self) -> str:
        return "FM"

    def get_modulation_parameters(self) -> dict[str]:
        return {"FM,SRC": self.source, "FM,DEVI": self.deviation}
