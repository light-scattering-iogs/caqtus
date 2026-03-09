from caqtus.types.iteration import StepsConfiguration
from caqtus.types.iteration._step_context import StepContext
from caqtus.types.parameter import Parameter
from .shots_manager import ShotScheduler


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
