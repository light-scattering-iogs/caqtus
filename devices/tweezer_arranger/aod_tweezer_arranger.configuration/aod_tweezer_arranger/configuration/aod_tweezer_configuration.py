from typing import Iterable, SupportsFloat

from settings_model import YAMLSerializable
from tweezer_arranger.configuration import TweezerConfiguration2D, TweezerLabel
from util import attrs


def to_tuple_of_float(values: Iterable[SupportsFloat]) -> tuple[float, ...]:
    return tuple(float(v) for v in values)


@attrs.define(slots=False)
class AODTweezerConfiguration(TweezerConfiguration2D):
    """Contains the information to generate a grid of trap with an AOD/AWG.

    Fields:
        frequencies_x: The frequencies of each tone in Hz.
        phases_x: The phases of each tone in radian.
        amplitudes_x: The amplitudes of each tone. They have no dimension.
        scale_x: The value to multiply the x-signal by to get the voltage to send to the AWG. Must be in V.
        frequencies_y: The frequencies of each tone in Hz.
        phases_y: The phases of each tone in radian.
        amplitudes_y: The amplitudes of each tone. They have no dimension.
        scale_y: The value to multiply the y-signal by to get the voltage to send to the AWG. Must be in V.
        sampling_rate: The sampling rate of the AWG to generate the signal, in Hz.
        number_samples: The number of samples of the waveform. To generate a signal for longer times than
        number_samples / sampling_rate, the waveform is repeated.
    """

    frequencies_x: tuple[float, ...] = attrs.field(
        converter=to_tuple_of_float, on_setattr=attrs.setters.convert
    )
    phases_x: tuple[float, ...] = attrs.field(
        converter=to_tuple_of_float, on_setattr=attrs.setters.convert
    )
    amplitudes_x: tuple[float, ...] = attrs.field(
        converter=to_tuple_of_float, on_setattr=attrs.setters.convert
    )
    scale_x: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0.0),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    frequencies_y: tuple[float, ...] = attrs.field(
        converter=to_tuple_of_float, on_setattr=attrs.setters.convert
    )
    phases_y: tuple[float, ...] = attrs.field(
        converter=to_tuple_of_float, on_setattr=attrs.setters.convert
    )
    amplitudes_y: tuple[float, ...] = attrs.field(
        converter=to_tuple_of_float, on_setattr=attrs.setters.convert
    )
    scale_y: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0.0),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    sampling_rate: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0.0),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    number_samples: int = attrs.field(
        converter=int,
        validator=attrs.validators.ge(1),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    @frequencies_x.validator  # type: ignore
    def validate_frequencies_x(self, _, frequencies_x):
        if not all(f >= 0 for f in frequencies_x):
            raise ValueError("Frequencies must be positive.")

    @frequencies_y.validator  # type: ignore
    def validate_frequencies_y(self, _, frequencies_y):
        if not all(f >= 0 for f in frequencies_y):
            raise ValueError("Frequencies must be positive.")

    @phases_x.validator  # type: ignore
    def validate_phases_x(self, _, phases_x):
        if not len(phases_x) == len(self.frequencies_x):
            raise ValueError(
                "The number of phases must be equal to the number of frequencies."
            )

    @phases_y.validator  # type: ignore
    def validate_phases_y(self, _, phases_y):
        if not len(phases_y) == len(self.frequencies_y):
            raise ValueError(
                "The number of phases must be equal to the number of frequencies."
            )

    @amplitudes_x.validator  # type: ignore
    def validate_amplitude_x(self, _, amplitude_x):
        if not len(amplitude_x) == len(self.frequencies_x):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )

    @amplitudes_y.validator  # type: ignore
    def validate_amplitude_y(self, _, amplitude_y):
        if not len(amplitude_y) == len(self.frequencies_y):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )

    @property
    def number_tweezers(self) -> int:
        return self.number_tweezers_along_x * self.number_tweezers_along_y

    @property
    def number_tweezers_along_x(self) -> int:
        return len(self.frequencies_x)

    @property
    def number_tweezers_along_y(self) -> int:
        return len(self.frequencies_y)

    def tweezer_positions(self) -> dict[TweezerLabel, tuple[float, float]]:
        positions: dict[TweezerLabel, tuple[float, float]] = {}
        for i, f_x in enumerate(self.frequencies_x):
            for j, f_y in enumerate(self.frequencies_y):
                positions[(i, j)] = (f_x * 1e-6, f_y * 1e-6)
        return positions

    def tweezer_labels(self) -> set[TweezerLabel]:
        return set(self.tweezer_positions().keys())

    @property
    def position_units(self) -> str:
        return "MHz"


YAMLSerializable.register_attrs_class(AODTweezerConfiguration)
