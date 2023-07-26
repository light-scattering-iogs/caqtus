from collections.abc import Iterable
from typing import TypeVar, Sequence

from pydantic import validator

from aod_tweezer_arranger.configuration import AODTweezerConfiguration
from spectum_awg_m4i66xx_x8.configuration import (
    SpectrumAWGM4i66xxX8Configuration,
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


class AODTweezerArranger(TweezerArranger[AODTweezerConfiguration]):
    awg_configuration: SpectrumAWGM4i66xxX8Configuration

    _awg: SpectrumAWGM4i66xxX8

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
        # self._awg.stop()

    def _prepare_awg(self) -> SpectrumAWGM4i66xxX8:
        first_config = first(self.tweezer_configurations.values())
        return SpectrumAWGM4i66xxX8(
            name=f"{self.name}_awg",
            board_id=self.awg_configuration.board_id,
            channel_settings=(
                ChannelSettings(
                    name="X",
                    enabled=True,
                    amplitude=first_config.scale_x,
                    maximum_power=self.awg_configuration.channel_settings[
                        0
                    ].maximum_power,
                ),
                ChannelSettings(
                    name="Y",
                    enabled=True,
                    amplitude=first_config.scale_y,
                    maximum_power=self.awg_configuration.channel_settings[
                        1
                    ].maximum_power,
                ),
            ),
            segment_names={SegmentName("segment 0")},
            steps={
                StepName("Step 0"): StepConfiguration(
                    segment=SegmentName("segment 0"),
                    next_step=StepName("Step 0"),
                    repetition=1,
                )
            },
            first_step=StepName("Step 0"),
            sampling_rate=round(first_config.sampling_rate),
        )

    def update_parameters(self, *, instructions: Sequence[ArrangerInstruction]) -> None:
        raise NotImplementedError


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))
