from collections.abc import Iterable
from typing import Optional

import numpy
import yaml

from expression import Expression
from sequence.configuration.steps.step import Step, compute_total_number_shots
from settings_model import YAMLSerializable
from units import Quantity, units
from util import attrs, serialization
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
        super().__init__(parent=parent, children=children)
        self.name = name
        self.start = start
        self.stop = stop
        self.step = step

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


def unstructure_hook(arange_loop: ArangeLoop) -> dict:
    return {
        "name": str(arange_loop.name),
        "start": serialization.unstructure(arange_loop.start, Expression),
        "stop": serialization.unstructure(arange_loop.stop, Expression),
        "step": serialization.unstructure(arange_loop.step, Expression),
        "children": serialization.unstructure(arange_loop.children, tuple[Step, ...]),
    }


serialization.register_unstructure_hook(ArangeLoop, unstructure_hook)


def structure_hook(data: dict, cls: type[ArangeLoop]) -> ArangeLoop:
    return ArangeLoop(
        name=DottedVariableName(data["name"]),
        start=serialization.structure(data["start"], Expression),
        stop=serialization.structure(data["stop"], Expression),
        step=serialization.structure(data["step"], Expression),
        children=serialization.structure(data["children"], tuple[Step, ...]),
    )


serialization.register_structure_hook(ArangeLoop, structure_hook)


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


YAMLSerializable.get_dumper().add_representer(ArangeLoop, representer)


def constructor(loader: yaml.Loader, node: yaml.Node):
    mapping = loader.construct_mapping(node, deep=True)
    try:
        return ArangeLoop(**mapping)
    except Exception as e:
        raise ValueError(
            f"Cannot construct {ArangeLoop.__name__} from {mapping}"
        ) from e


YAMLSerializable.get_loader().add_constructor(f"!{ArangeLoop.__name__}", constructor)
