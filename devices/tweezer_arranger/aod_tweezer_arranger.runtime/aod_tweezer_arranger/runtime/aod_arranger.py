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
from tweezer_arranger.runtime import (
    TweezerArranger,
    ArrangerInstruction,
    HoldTweezers,
    MoveTweezers,
    RearrangeTweezers,
)
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
        pass
        # self._awg = self._prepare_awg()
        # self._enter_context(self._awg)
        # self._signal_generator = SignalGenerator(self.sampling_rate)
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
            segment_names=_get_segment_names(self.tweezer_sequence),
            steps=_get_steps(self.tweezer_sequence),
            first_step=StepName(last),
            sampling_rate=self.sampling_rate,
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

    def update_parameters(
        self, *, tweezer_sequence_durations: Sequence[float]
    ) -> None:
        raise NotImplementedError


def move_segment_name(step: int) -> SegmentName:
    return SegmentName(f"Move segment {step}")


def rearrange_segment_name(step: int) -> SegmentName:
    return SegmentName(f"Rearrange segment {step}")


def static_segment_names(
    step: int,
) -> tuple[SegmentName, SegmentName]:
    return SegmentName(f"Static segment {step} integral part"), SegmentName(
        f"Static segment {step} fractional part"
    )


def static_step_names(
    step: int,
) -> tuple[StepName, StepName]:
    return StepName(f"Static step {step} integral part"), StepName(
        f"Static step {step} fractional part"
    )

def move_step_name(step: int) -> StepName:
    return StepName(f"Move step {step}")


def rearrange_step_name(step: int) -> StepName:
    return StepName(f"Rearrange step {step}")


def _get_segment_names(
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> set[SegmentName]:
    segments = set[SegmentName]()
    for step, instruction in enumerate(tweezer_sequence):
        match instruction:
            case HoldTweezers():
                integral_part, fraction_part = static_segment_names(step)
                segments.add(integral_part)
                segments.add(fraction_part)
            case MoveTweezers():
                segments.add(move_segment_name(step))
            case RearrangeTweezers():
                segments.add(move_segment_name(step))
            case _:
                raise NotImplementedError
    # We add a segment for the last step to just loop over the last configuration
    integral_part, _ = static_segment_names(len(tweezer_sequence))
    segments.add(integral_part)
    return segments


def _get_next_step(
    current_step: int,
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> StepName:
    if current_step == len(tweezer_sequence) - 1:
        return static_step_names(len(tweezer_sequence))[0]
    else:
        next_step_instruction = tweezer_sequence[current_step + 1]
        match next_step_instruction:
            case HoldTweezers():
                return static_step_names(current_step + 1)[0]
            case MoveTweezers():
                return move_step_name(current_step + 1)
            case RearrangeTweezers():
                return rearrange_step_name(current_step + 1)


def _get_steps(
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> dict[StepName, StepConfiguration]:
    steps = dict[StepName, StepConfiguration]()
    for index, instruction in enumerate(tweezer_sequence):
        match instruction:
            case HoldTweezers():
                integral_step_part, fractional_step_part = static_step_names(index)
                integral_segment_part, fractional_segment_part = static_segment_names(
                    index
                )

                # Here the repetition is not correct, we'll need to update before starting the AWG sequence
                steps[integral_step_part] = StepConfiguration(
                    segment=integral_segment_part,
                    next_step=fractional_step_part,
                    repetition=1,
                )
                steps[fractional_step_part] = StepConfiguration(
                    segment=fractional_segment_part,
                    next_step=_get_next_step(index, tweezer_sequence),
                    repetition=1,
                )
            case MoveTweezers():
                steps[move_step_name(index)] = StepConfiguration(
                    segment=move_segment_name(index),
                    next_step=_get_next_step(index, tweezer_sequence),
                    repetition=1,
                )
            case RearrangeTweezers():
                steps[rearrange_step_name(index)] = StepConfiguration(
                    segment=rearrange_segment_name(index),
                    next_step=_get_next_step(index, tweezer_sequence),
                    repetition=1,
                )
            case _:
                raise NotImplementedError
    last_step = static_step_names(len(tweezer_sequence))[0]
    last_segment = static_segment_names(len(tweezer_sequence))[0]
    steps[last_step] = StepConfiguration(
        segment=last_segment,
        next_step=last_step,
        repetition=1,
    )
    return steps


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))
