import numpy

from expression import Expression
from units import units, Quantity, DimensionalityError, ureg, dimensionless
from .shot_configuration import ShotConfiguration


def evaluate_step_durations(shot: ShotConfiguration, context: dict[str]) -> list[float]:
    """Compute the duration of each step in the shot

    This function evaluates all the step duration expressions by replacing the variables with their numerical values
    provided in 'context'. It returns a list of all step durations in seconds.
    """

    durations = []
    for name, expression in zip(shot.step_names, shot.step_durations):
        duration = Quantity(expression.evaluate(context | units))
        try:
            durations.append(duration.to("s").magnitude)
        except DimensionalityError as err:
            err.extra_msg = f" for the duration ({expression.body}) of step '{name}'"
            raise err
    return durations


def evaluate_analog_local_times(
    shot: ShotConfiguration,
    step_durations: list[float],
    analog_time_step: float,
    digital_time_step: float,
) -> list[numpy.ndarray]:
    """Compute new time points within each step to evaluate analog ramps"""

    analog_times = []
    last_analog_time = -numpy.inf
    for step, duration in enumerate(step_durations):
        is_step_of_constants = all(
            _is_constant(lane.get_effective_value(step)) for lane in shot.analog_lanes
        )
        start = max(last_analog_time + analog_time_step, digital_time_step)
        stop = duration - analog_time_step
        if is_step_of_constants:
            if stop > start + analog_time_step:
                step_analog_times = numpy.array([start])
            else:
                step_analog_times = numpy.array([])
        else:
            step_analog_times = numpy.arange(
                start,
                stop,
                analog_time_step,
            )
        if len(step_analog_times) > 0:
            last_analog_time = step_analog_times[-1]
        last_analog_time -= duration
        analog_times.append(step_analog_times)
    return analog_times


def evaluate_analog_values(
    shot: ShotConfiguration, analog_times: list[numpy.ndarray], context: dict[str]
) -> dict[str, Quantity]:
    """Computes the analog values of each lanes in lane units"""
    result = {}
    for lane in shot.analog_lanes:
        lane_has_dimension = not Quantity(1, units=lane.units).is_compatible_with(
            dimensionless
        )
        values = []
        for step in range(len(shot.step_names)):
            expression = lane.get_effective_value(step)
            if _is_constant(expression):
                try:
                    value = Quantity(expression.evaluate(context | units))
                except NameError as err:
                    raise NameError(
                        f"'{err.name}' is no defined in expression '{expression.body}' "
                        f"(step: {shot.step_names[step]}, lane: {lane.name})"
                    )
                if value.is_compatible_with(dimensionless) and lane_has_dimension:
                    value = Quantity(
                        value.to(dimensionless).magnitude, units=lane.units
                    )
                else:
                    value = value.to(lane.units)
                values.append(numpy.full_like(analog_times[step], value.magnitude))
            else:
                try:
                    value = Quantity(
                        expression.evaluate(
                            context | units | {"t": analog_times[step] * ureg.s}
                        )
                    )
                except NameError as err:
                    raise NameError(
                        f"'{err.name}' is no defined in expression '{expression.body}' "
                        f"(step: {shot.step_names[step]}, lane: {lane.name})"
                    )
                if value.is_compatible_with(dimensionless) and lane_has_dimension:
                    value = Quantity(
                        value.to(dimensionless).magnitude, units=lane.units
                    )
                else:
                    value = value.to(lane.units)
                values.append(value.magnitude)

        result[lane.name] = numpy.concatenate(values) * Quantity(1, units=lane.units)

    return result


def _is_constant(expression: Expression):
    return "t" not in expression.upstream_variables
