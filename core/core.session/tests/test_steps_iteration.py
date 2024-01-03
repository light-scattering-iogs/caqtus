from core.session.sequence.iteration_configuration import (
    StepsConfiguration,
)
from .steps_iteration import steps_configuration


def test_serialization(steps_configuration: StepsConfiguration):
    assert steps_configuration == StepsConfiguration.load(
        StepsConfiguration.dump(steps_configuration)
    )
