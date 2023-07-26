import logging

from aod_tweezer_arranger.runtime.aod_arranger import _get_steps
from tweezer_arranger.configuration import TweezerConfigurationName
from tweezer_arranger.runtime import HoldTweezers, MoveTweezers

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)


def test_segment_names():
    sequence = (
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
        MoveTweezers(
            initial_tweezer_configuration=TweezerConfigurationName("5x5 tweezers"),
            final_tweezer_configuration=TweezerConfigurationName("5x5 tweezers"),
        ),
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
    )


def test_steps():
    sequence = (
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
        MoveTweezers(
            initial_tweezer_configuration=TweezerConfigurationName("5x5 tweezers"),
            final_tweezer_configuration=TweezerConfigurationName("5x5 tweezers"),
        ),
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
    )
    for step_name, config in _get_steps(sequence).items():
        logger.debug(f"{step_name}: {config}")
    assert False
