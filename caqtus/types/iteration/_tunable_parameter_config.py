import attrs
import cattrs

from caqtus.types.expression import Expression, configure_expression_conversion_hooks
from caqtus.utils.serialization import configure_external_union


@attrs.define
class AnalogInputRange:
    """Defines an unevaluated range of values for an analog user input.

    Attributes:
        min_value: The minimum value of the range.
        max_value: The maximum value of the range.
    """

    min_value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression)
    )
    max_value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression)
    )


@attrs.define
class DigitalInput:
    """Indicates a digital user input."""

    pass


type TunableParameterConfig = AnalogInputRange | DigitalInput


def configure_tunable_parameter_conversion_hooks(converter: cattrs.Converter) -> None:
    """Set up a converter to handle TunableParameterConfig types."""

    configure_expression_conversion_hooks(converter)
    configure_external_union(TunableParameterConfig.__value__, converter)
