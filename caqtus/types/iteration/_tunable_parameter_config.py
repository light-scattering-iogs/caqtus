from collections.abc import Mapping
from typing import assert_never

import attrs
import cattrs

from caqtus.types.expression import Expression, configure_expression_conversion_hooks
from caqtus.types.parameter import Parameter, is_parameter
from caqtus.types.units import Quantity, Unit, dimensionless
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils.serialization import configure_external_union


@attrs.define
class AnalogRangeConfig:
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
class DigitalInputConfig:
    """Indicates a digital user input."""

    pass


type TunableParameterConfig = AnalogRangeConfig | DigitalInputConfig


def configure_tunable_parameter_conversion_hooks(converter: cattrs.Converter) -> None:
    """Set up a converter to handle TunableParameterConfig types."""

    configure_expression_conversion_hooks(converter)
    configure_external_union(TunableParameterConfig.__value__, converter)


@attrs.frozen
class AnalogRange:
    """A class representing an analog range with a minimum and maximum value.

    Attributes:
        minimum: The minimum value of the analog range.

        maximum: The maximum value of the analog range.

        unit: The unit of the analog range.

        It is not required to be in base units since it is a user-facing unit.
    """

    minimum: float
    maximum: float
    unit: Unit


@attrs.define
class DigitalInput:
    """Indicates a digital user input."""

    pass


type InputType = AnalogRange | DigitalInput

type InputSchema = Mapping[DottedVariableName, InputType]
"""A mapping from variable names to input types, defining the schema for user inputs."""


def evaluate_tunable_parameter_configs(
    tunable_params: Mapping[DottedVariableName, TunableParameterConfig],
    initial_parameters: Mapping[DottedVariableName, Parameter],
) -> InputSchema:
    """Evaluate a mapping of TunableParameterConfig.

    Args:
        tunable_params: The mapping of TunableParameterConfig to evaluate.
        initial_parameters: The value of the constant parameters defined before the
            iteration starts.
    """

    return {
        variable_name: evaluate_tunable_parameter_config(
            tunable_param, initial_parameters
        )
        for variable_name, tunable_param in tunable_params.items()
    }


def evaluate_tunable_parameter_config(
    tunable_param: TunableParameterConfig,
    initial_parameters: Mapping[DottedVariableName, Parameter],
) -> InputType:
    """Evaluate a TunableParameterConfig.

    Args:
        tunable_param: The TunableParameterConfig to evaluate.
        initial_parameters: The value of the constant parameters defined before the
            iteration starts.
    """

    match tunable_param:
        case DigitalInputConfig():
            return DigitalInput()
        case AnalogRangeConfig(min_value, max_value):
            minimum = min_value.evaluate(initial_parameters)
            maximum = max_value.evaluate(initial_parameters)
            if not is_parameter(minimum):
                raise TypeError(
                    f"Lower bound {min_value} does not evaluate to a parameter, got "
                    f"{type(minimum)}"
                )
            if not is_parameter(maximum):
                raise TypeError(
                    f"Upper bound {max_value} does not evaluate to a parameter, got "
                    f"{type(maximum)}"
                )
            try:
                return analog_bounds_to_range(minimum, maximum)
            except Exception as e:
                raise TypeError(
                    f"Failed to convert bounds {min_value} and {max_value} to an "
                    "analog range."
                ) from e
        case _:
            assert_never(tunable_param)


def analog_bounds_to_range(minimum: Parameter, maximum: Parameter) -> AnalogRange:
    if isinstance(minimum, bool):
        raise TypeError(
            "Lower bound evaluates to a boolean, which is not "
            "a valid type for an analog range."
        )
    if isinstance(maximum, bool):
        raise TypeError(
            "Upper bound evaluates to a boolean, which is not "
            "a valid type for an analog range."
        )
    match minimum:
        case int() | float():
            match maximum:
                case int() | float():
                    return AnalogRange(
                        minimum=float(minimum),
                        maximum=float(maximum),
                        unit=dimensionless,
                    )
                case Quantity():
                    if not maximum.is_compatible_with(dimensionless):
                        raise TypeError(
                            f"Upper bound {maximum} is not compatible with "
                            f"dimensionless"
                        )
                    return AnalogRange(
                        minimum=float(minimum),
                        maximum=maximum.to_unit(dimensionless).magnitude,
                        unit=dimensionless,
                    )
                case _:
                    assert_never(maximum)
        case Quantity():
            match maximum:
                case int() | float():
                    if not minimum.is_compatible_with(dimensionless):
                        raise TypeError(
                            f"Upper bound {maximum} is not compatible with "
                            f"{minimum.units}"
                        )
                    return AnalogRange(
                        minimum=minimum.magnitude,
                        maximum=Quantity(maximum, dimensionless)
                        .to_unit(minimum.units)
                        .magnitude,
                        unit=minimum.units,
                    )
                case Quantity():
                    if not minimum.is_compatible_with(maximum):
                        raise TypeError(
                            f"Lower bound {minimum} is not compatible with "
                            f"upper bound {maximum}"
                        )
                    return AnalogRange(
                        minimum=minimum.magnitude,
                        maximum=maximum.to_unit(minimum.units).magnitude,
                        unit=minimum.units,
                    )
                case _:
                    assert_never(maximum)
        case _:
            assert_never(minimum)
