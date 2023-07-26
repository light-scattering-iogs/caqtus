import logging

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
        tweezer_configurations={TweezerConfigurationName("5x5 tweezers"): static_tweezer_config},
        tweezer_sequence=sequence,
    )

    with arranger:
        pass
    assert False


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
    - 2.741850924835937
    - 1.3145083748276392
    - 6.170351129777032
    - 1.6014159109588775
    - 3.3156659532200905
    amplitudes_x: !tuple
    - 6454.284743801089
    - 5816.157558722016
    - 7474.554249262534
    - 5755.97176287821
    - 7088.695602001658
    scale_x: 0.369
    frequencies_y: !tuple
    - 72000430.22928502
    - 74250537.38676493
    - 76500644.54424484
    - 78750751.70172475
    - 81000858.85920466
    phases_y: !tuple
    - 1.4037027695018902
    - 4.504049754538404
    - 0.13955130558174356
    - 4.1719161118531005
    - 5.614661290202681
    amplitudes_y: !tuple
    - 6329.462033845358
    - 6985.471503754264
    - 6528.282132774126
    - 7167.660391022301
    - 5646.461984837907
    scale_y: 0.369
    sampling_rate: 625000000.0
    number_samples: 625248
    """

    return AODTweezerConfiguration.from_yaml(yaml)
