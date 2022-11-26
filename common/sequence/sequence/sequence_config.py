import math
from abc import ABC
from functools import singledispatch
from typing import Optional

import numpy
import yaml
from anytree import NodeMixin, RenderTree

from expression import Expression
from settings_model import SettingsModel
from settings_model.settings_model import YAMLSerializable
from sequence.shot import ShotConfiguration
from units import Quantity, units


class Step(NodeMixin, ABC):
    def __init__(
        self, parent: Optional["Step"] = None, children: Optional[list["Step"]] = None
    ):
        self.parent = parent
        if children is not None:
            self.children = children

    def row(self):
        if self.is_root:
            return 0
        else:
            for i, child in enumerate(self.parent.children):
                if child is self:
                    return i


class SequenceSteps(Step, YAMLSerializable):
    def __init__(
        self, parent: Optional["Step"] = None, children: Optional[list["Step"]] = None
    ):
        if not children:
            children = []
        super().__init__(parent, children)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "SequenceSteps"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"children": [child for child in step.children]},
        )

    def __repr__(self):
        return f"SequenceSteps(parent={self.parent}, children={self.children})"

    def __str__(self):
        return "\n".join(
            f"{pre}{node if not node is self else 'steps'}"
            for pre, _, node in RenderTree(self)
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))


class VariableDeclaration(Step, YAMLSerializable):
    def __init__(
        self, name: str, expression: Expression, parent: Optional["Step"] = None
    ):
        super().__init__(parent, None)
        self.name = name
        self.expression = expression

    def __repr__(self):
        return f"VariableDeclaration({self.name}, {self.expression})"

    def __str__(self):
        return f"{self.name} = {self.expression.body}"

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "VariableDeclaration"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"name": step.name, "expression": step.expression},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))


class LinspaceLoop(Step, YAMLSerializable):
    def __init__(
        self,
        name: str,
        start: Expression,
        stop: Expression,
        num: int,
        parent: Optional["Step"] = None,
        children: Optional[list["Step"]] = None,
    ):
        if not children:
            children = []
        super().__init__(parent, children)
        self.name = name
        self.start = start
        self.stop = stop
        self.num = num

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "LinspaceLoop"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
                "start": step.start,
                "stop": step.stop,
                "num": step.num,
                "children": [child for child in step.children],
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.num} steps"
        )


class ArangeLoop(Step, YAMLSerializable):
    def __init__(
        self,
        name: str,
        start: Expression,
        stop: Expression,
        step: Expression,
        parent: Optional["Step"] = None,
        children: Optional[list["Step"]] = None,
    ):
        if not children:
            children = []
        super().__init__(parent, children)
        self.name = name
        self.start = start
        self.stop = stop
        self.step = step

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "ArangeLoop"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
                "start": step.start,
                "stop": step.stop,
                "step": step.step,
                "children": [child for child in step.children],
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.step.body} spacing"
        )


class ExecuteShot(Step, YAMLSerializable):
    def __init__(self, name: str, parent: Optional[Step] = None):
        super().__init__(parent, None)
        self.name = name

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "ExecuteShot"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"name": step.name},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __str__(self):
        return f"Do {self.name}"


class SequenceConfig(SettingsModel):
    program: SequenceSteps
    shot_configurations: dict[str, ShotConfiguration]


# noinspection PyUnusedLocal
@singledispatch
def compute_number_shots(steps: Step):
    return 0


@compute_number_shots.register
def _(steps: SequenceSteps):
    return sum(compute_number_shots(step) for step in steps.children)


@compute_number_shots.register
def _(loop: LinspaceLoop):
    return loop.num * sum(compute_number_shots(step) for step in loop.children)


@compute_number_shots.register
def _(loop: ArangeLoop):
    try:
        start = Quantity(loop.start.evaluate(units))
        stop = Quantity(loop.stop.evaluate(units))
        step = Quantity(loop.step.evaluate(units))

        unit = start.units

        multiplier = len(
            numpy.arange(
                start.to(unit).magnitude,
                stop.to(unit).magnitude,
                step.to(unit).magnitude,
            )
        )
        return multiplier * sum(compute_number_shots(step) for step in loop.children)
    except Exception:
        return math.nan


# noinspection PyUnusedLocal
@compute_number_shots.register
def _(shot: ExecuteShot):
    return 1
