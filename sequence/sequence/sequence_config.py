from abc import ABC

from settings_model import SettingsModel


class Step(SettingsModel, ABC):
    pass


class StepsSequence(Step):
    steps: list[Step]


class VariableDeclaration(Step):
    name: str
    expression: str


class LinspaceLoop(Step):
    start: float
    stop: float
    num: int
    sub_steps: StepsSequence


class SequenceConfig(SettingsModel):
    program: StepsSequence
