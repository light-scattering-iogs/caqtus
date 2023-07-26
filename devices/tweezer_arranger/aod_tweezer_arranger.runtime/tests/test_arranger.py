import logging
import time

import pytest

from aod_tweezer_arranger.configuration import AODTweezerConfiguration
from aod_tweezer_arranger.runtime.aod_arranger import (
    _get_steps,
    _get_segment_names,
    AODTweezerArranger,
)
from device.name import DeviceName
from tweezer_arranger.configuration import TweezerConfigurationName
from tweezer_arranger.runtime import HoldTweezers, MoveTweezers

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def sequence():
    return (
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
        MoveTweezers(
            initial_tweezer_configuration=TweezerConfigurationName("5x5 tweezers"),
            final_tweezer_configuration=TweezerConfigurationName("5x5 tweezers"),
        ),
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
    )


def test_segment_names(sequence):
    _get_segment_names(sequence)


def test_steps(sequence):
    for step_name, config in _get_steps(sequence).items():
        logger.debug(f"{step_name}: {config}")


def test_arranger_initialization(sequence, static_tweezer_config):
    arranger = AODTweezerArranger(
        name=DeviceName("AOD Tweezer Arranger"),
        awg_board_id="/dev/spcm0",
        awg_max_power_x=-4,
        awg_max_power_y=-4,
        tweezer_configurations={
            TweezerConfigurationName("5x5 tweezers"): static_tweezer_config
        },
        tweezer_sequence=sequence,
    )

    with arranger:
        pass


def test_simple_hold(static_tweezer_config):
    sequence = (
        HoldTweezers(tweezer_configuration=TweezerConfigurationName("5x5 tweezers")),
    )
    arranger = AODTweezerArranger(
        name=DeviceName("AOD Tweezer Arranger"),
        awg_board_id="/dev/spcm0",
        awg_max_power_x=-4,
        awg_max_power_y=-4,
        tweezer_configurations={
            TweezerConfigurationName("5x5 tweezers"): static_tweezer_config
        },
        tweezer_sequence=sequence,
    )

    with arranger:
        arranger.update_parameters(tweezer_sequence_durations=[1.0])
        arranger.start_sequence()
        logger.debug(arranger.has_sequence_finished())
        time.sleep(1.5)
        logger.debug(arranger.has_sequence_finished())


@pytest.fixture
def static_tweezer_config():
    yaml = """
    !AODTweezerConfiguration
      frequencies_x: !tuple
      - 77000446.22293873
      - 79250553.38041864
      - 81500660.53789856
      - 83750767.69537847
      - 86000874.85285838
      phases_x: !tuple
      - 0.7067887018319592
      - 4.527396840340979
      - 2.0648674145312205
      - 2.743891038343444
      - 3.4229024846094105
      amplitudes_x: !tuple
      - 0.19910714858840603
      - 0.1707220728893671
      - 0.22838376548191175
      - 0.1791999040035731
      - 0.21665310355211953
      scale_x: 0.36895121628746536
      frequencies_y: !tuple
      - 72000430.22928502
      - 74250537.38676493
      - 76500644.54424484
      - 78750751.70172475
      - 81000858.85920466
      phases_y: !tuple
      - 1.6860165014548594
      - 5.391079116990225
      - 2.8128509532569117
      - 3.3763285252427617
      - 3.9397454981115954
      amplitudes_y: !tuple
      - 0.19602577961600803
      - 0.17609182816645083
      - 0.22085623211326327
      - 0.17921150825621476
      - 0.22287063921521538
      scale_y: 0.36895121628746536
      sampling_rate: 625000000.0
      number_samples: 625248
    """

    return AODTweezerConfiguration.from_yaml(yaml)
