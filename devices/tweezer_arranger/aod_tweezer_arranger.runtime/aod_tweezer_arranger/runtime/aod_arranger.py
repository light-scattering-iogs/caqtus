import logging
from collections.abc import Iterable
from typing import TypeVar, Sequence

from pydantic import validator

from aod_tweezer_arranger.configuration import AODTweezerConfiguration
from spectum_awg_m4i66xx_x8.configuration import (
    ChannelSettings,
)
from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    SegmentName,
    StepName,
    StepConfiguration,
)
from tweezer_arranger.configuration import (
    TweezerConfigurationName,
)
from tweezer_arranger.runtime import TweezerArranger, ArrangerInstruction
from .signal_generator import AWGSignalArray, SignalGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AODTweezerArranger(TweezerArranger[AODTweezerConfiguration]):
    """Device that uses an AWG/AOD to rearrange and move tweezers.

    Fields:
        awg_board_id: The ID of the AWG board to use. Must be a SpectrumAWGM4i66xxX8 board.
        awg_max_power_x: The maximum power that can be output by the AWG on the X axis, in dBm.
        awg_max_power_y: The maximum power that can be output by the AWG on the Y axis, in dBm.
    """

    awg_board_id: str
    awg_max_power_x: float
    awg_max_power_y: float

    _awg: SpectrumAWGM4i66xxX8
    _static_signals: dict[
        TweezerConfigurationName, tuple[AWGSignalArray, AWGSignalArray]
    ]
    _signal_generator: SignalGenerator

    @validator("tweezer_configurations")
    def validate_tweezer_configurations(
        cls, configurations: dict[TweezerConfigurationName, AODTweezerConfiguration]
    ) -> dict[TweezerConfigurationName, AODTweezerConfiguration]:
        first_config = first(configurations.values())
        for config in configurations.values():
            if config.scale_x != first_config.scale_x:
                raise ValueError(
                    "All AODTweezerConfigurations must have the same scale_x"
                )
            if config.scale_y != first_config.scale_y:
                raise ValueError(
                    "All AODTweezerConfigurations must have the same scale_y"
                )
            if config.sampling_rate != first_config.sampling_rate:
                raise ValueError(
                    "All AODTweezerConfigurations must have the same sampling_rate"
                )
        return configurations

    def initialize(self) -> None:
        self._awg = self._prepare_awg()
        self._enter_context(self._awg)
        self._signal_generator = SignalGenerator(self.sampling_rate)
        # self._awg.stop()

    def _prepare_awg(self) -> SpectrumAWGM4i66xxX8:
        steps: dict[StepName, StepConfiguration] = {}
        segment_names: set[SegmentName] = set()
        last = "last"
        for config_name, tweezer_config in self.tweezer_configurations.values():
            integer = f"{config_name}.integer"
            fractional = f"{config_name}.fractional"

            # Here the next_step and repetition are not correct, we'll need to update before starting the AWG sequence
            steps[StepName(integer)] = StepConfiguration(
                segment=SegmentName(integer),
                next_step=StepName(fractional),
                repetition=1,
            )
            segment_names.add(SegmentName(integer))
            steps[StepName(fractional)] = StepConfiguration(
                segment=SegmentName(fractional),
                next_step=StepName(last),
                repetition=1,
            )
            segment_names.add(SegmentName(fractional))

            logger.debug(f"Computing signal for {config_name}")
            signal_x = self._signal_generator.generate_signal_static_traps(
                tweezer_config.amplitudes_x,
                tweezer_config.frequencies_x,
                tweezer_config.phases_x,
                tweezer_config.number_samples,
            )
            signal_y = self._signal_generator.generate_signal_static_traps(
                tweezer_config.amplitudes_y,
                tweezer_config.frequencies_y,
                tweezer_config.phases_y,
                tweezer_config.number_samples,
            )
            self._static_signals[config_name] = (signal_x, signal_y)
        steps[StepName(last)] = StepConfiguration(
            segment=SegmentName(last),
            next_step=StepName(last),
            repetition=1,
        )
        segment_names.add(SegmentName(last))

        return SpectrumAWGM4i66xxX8(
            name=f"{self.name}_awg",
            board_id=self.awg_board_id,
            channel_settings=(
                ChannelSettings(
                    name="X",
                    enabled=True,
                    amplitude=self.scale_x,
                    maximum_power=self.awg_max_power_x,
                ),
                ChannelSettings(
                    name="Y",
                    enabled=True,
                    amplitude=self.scale_y,
                    maximum_power=self.awg_max_power_y,
                ),
            ),
            segment_names=segment_names,
            steps=steps,
            first_step=StepName(last),
            sampling_rate=round(self.sampling_rate),
        )

    @property
    def sampling_rate(self) -> int:
        first_config = first(self.tweezer_configurations.values())
        return round(first_config.sampling_rate)

    @property
    def scale_x(self) -> float:
        first_config = first(self.tweezer_configurations.values())
        return first_config.scale_x

    @property
    def scale_y(self) -> float:
        first_config = first(self.tweezer_configurations.values())
        return first_config.scale_y

    def update_parameters(self, *, instructions: Sequence[ArrangerInstruction]) -> None:
        raise NotImplementedError


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))
