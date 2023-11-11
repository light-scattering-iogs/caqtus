from collections.abc import Iterable
from typing import Optional

import numpy
import yaml

from expression import Expression
from sequence.configuration.steps.step import Step, compute_total_number_shots
from units import Quantity, units
from util import attrs
from variable.name import DottedVariableName


@attrs.define
class ArangeLoop(Step):
    """Represent a loop over a variable with constant step size for this variable."""

    name: DottedVariableName = attrs.field(
        validator=attrs.validators.instance_of(DottedVariableName),
        on_setattr=attrs.setters.validate,
    )
    start: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    stop: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    step: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __init__(
        self,
        name: DottedVariableName,
        start: Expression,
        stop: Expression,
        step: Expression,
        parent: Optional[Step] = None,
        children: Optional[Iterable[Step]] = None,
    ):
        self.__attrs_init__(name, start, stop, step, parent, children)
        if not children:
            children = []
        super().__init__(parent, children)

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.step.body} spacing"
        )

    def __eq__(self, other):
        if not isinstance(other, ArangeLoop):
            return NotImplemented
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


def representer(dumper: yaml.Dumper, step: ArangeLoop):
    return dumper.represent_mapping(
        f"!{ArangeLoop.__name__}",
        {
            "name": step.name,
            "start": step.start,
            "stop": step.stop,
            "step": step.step,
            "children": [child for child in step.children],
        },
    )


def constructor(loader: yaml.Loader, node: yaml.Node):
    mapping = loader.construct_mapping(node, deep=True)
    try:
        return ArangeLoop(**mapping)
    except Exception as e:
        raise ValueError(
            f"Cannot construct {ArangeLoop.__name__} from {mapping}"
        ) from e
