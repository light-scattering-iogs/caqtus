from abc import ABC

from pydantic import BaseModel, Field


class Instruction(BaseModel, ABC):
    pass


class Continue(Instruction):
    values: list[bool]
    duration: float = Field(units="s")


class Stop(Instruction):
    values: list[bool]


class Loop(Instruction):
    repetitions: int
    start_values: list[bool]
    start_duration: float = Field(units="s")
    end_values: list[bool]
    end_duration: float = Field(units="s")
