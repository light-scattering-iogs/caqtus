from abc import ABC

import pydantic


class Instruction(pydantic.BaseModel, ABC):
    pass

class Continue(Instruction):
    values: list[bool]
    duration: float

class Loop(Instruction):
    start_values: list[bool]
    start_duration: float
    end_values: list[bool]
    end_duration: float
