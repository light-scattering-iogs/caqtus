from abc import ABC
from typing import Union

from settings_model import SettingsModel


class Step(SettingsModel, ABC):
    pass


class StepsSequence(Step):
    steps: list[Step]


class VariableDeclaration(Step):
    name: str
    expression: str


class GroupDeclaration(Step):
    name: str
    variables: list[Union["GroupDeclaration", VariableDeclaration]]


class LinspaceIteration(Step):
    name: str
    start: str
    stop: str
    num: int
    sub_steps: list[Step]

class ExecuteShot(Step):
    name: str



class SequenceConfig(SettingsModel):
    program: StepsSequence
