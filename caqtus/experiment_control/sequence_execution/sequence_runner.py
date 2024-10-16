import caqtus.formatter as fmt
from caqtus.types.iteration import StepsConfiguration
from caqtus.types.parameter import is_parameter, Parameter, ParameterNamespace
from caqtus.types.recoverable_exceptions import InvalidTypeError
from .shots_manager import ShotScheduler
from .step_context import StepContext


async def execute_steps(
    steps: StepsConfiguration,
    initial_context: StepContext[Parameter],
    shot_scheduler: ShotScheduler,
):
    """Execute a sequence of steps on the experiment.

    This method will recursively execute each step in the sequence passed as
    argument and scheduling the shots when encountering a shot step.
    """

    for context in steps.walk(initial_context):
        await shot_scheduler.schedule_shot(context.variables)


def evaluate_initial_context(parameters: ParameterNamespace) -> StepContext:
    """Evaluate the initial context of the sequence from the parameters."""

    flat_parameters = parameters.flatten()

    context = StepContext[Parameter]()

    for name, expression in flat_parameters:
        value = expression.evaluate({})
        if not is_parameter(value):
            raise InvalidTypeError(
                f"{fmt.expression(value)} for {fmt.shot_param(name)} does not evaluate "
                f"to a parameter, but to {fmt.type_(type(value))}",
            )
        context = context.update_variable(name, value)

    return context
