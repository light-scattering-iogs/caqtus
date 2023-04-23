from typing import Optional, Self

import numpy
import yaml

from expression import Expression
from sequence.configuration.steps.step import Step, compute_total_number_shots
from settings_model import YAMLSerializable, validate_arguments
from units import Quantity, units
from variable.name import DottedVariableName


class ArangeLoop(Step, YAMLSerializable):
    @validate_arguments
    def __init__(
        self,
        name: DottedVariableName,
        start: Expression,
        stop: Expression,
        step: Expression,
        parent: Optional[Step] = None,
        children: Optional[list[Step]] = None,
    ):
        self.name = name
        self.start = start
        self.stop = stop
        self.step = step
        if not children:
            children = []
        Step.__init__(self, parent, children)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: Self):
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
        mapping = loader.construct_mapping(node)
        try:
            return cls(**mapping)
        except Exception as e:
            raise ValueError(f"Cannot construct {cls.__name__} from {mapping}") from e

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.step.body} spacing"
        )

    def __eq__(self, other):
        if not isinstance(other, ArangeLoop):
            return False
        return (
            self.name == other.name
            and self.start == other.start
            and self.stop == other.stop
            and self.step == other.step
            and self.children == other.children
        )

    def expected_number_shots(self) -> Optional[int]:
        number_sub_steps = compute_total_number_shots(self.children)
        if number_sub_steps is None:
            return None
        try:
            start = Quantity(self.start.evaluate(units))
            stop = Quantity(self.stop.evaluate(units))
            step = Quantity(self.step.evaluate(units))

            unit = start.units

            multiplier = len(
                numpy.arange(
                    start.to(unit).magnitude,
                    stop.to(unit).magnitude,
                    step.to(unit).magnitude,
                )
            )
            return multiplier * number_sub_steps
        except Exception:
            return None
