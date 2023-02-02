import logging
from abc import ABC, abstractmethod
from typing import Literal, Any

from pydantic import Field, validator

from settings_model import SettingsModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SiglentSDG6000XModulation(SettingsModel, ABC):
    source: Literal["INT", "EXT", "CH1", "CH2"] = Field(
        default="EXT", allow_mutation=False
    )

    @validator("source")
    def validate_source(cls, source):
        if source == "INT":
            raise NotImplementedError("Internal modulation source is not implemented")
        if source == "CH1" or source == "CH2":
            raise NotImplementedError("Inter channels modulation is not implemented")
        return source

    @abstractmethod
    def get_modulation_type(self) -> str:
        ...

    @abstractmethod
    def get_modulation_parameters(self) -> list[tuple[str, Any]]:
        ...

    class Config:
        validate_assignment = True
        validate_all = True


class AmplitudeModulation(SiglentSDG6000XModulation):
    depth: float = Field(default=100, units="%", allow_mutation=False)

    def get_modulation_type(self) -> str:
        return "AM"

    def get_modulation_parameters(self):
        return [("AM,SRC", self.source), ("AM,DEPTH", self.depth)]


class FrequencyModulation(SiglentSDG6000XModulation):
    deviation: float = Field(ge=0, units="Hz", allow_mutation=False)

    def get_modulation_type(self) -> str:
        return "FM"

    def get_modulation_parameters(self):
        return [("FM,SRC", self.source), ("FM,DEVI", self.deviation)]
