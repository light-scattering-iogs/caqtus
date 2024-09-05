from decimal import Decimal
from typing import Type

from caqtus.device.sequencer import (
    SequencerConfiguration,
    AnalogChannelConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
)
from caqtus.device.sequencer.channel_commands import (
    CalibratedAnalogMapping,
    LaneValues,
    Constant,
    DeviceTrigger,
)
from caqtus.device.sequencer.channel_commands.timing import BroadenLeft
from caqtus.device.sequencer.trigger import (
    ExternalClockOnChange,
    TriggerEdge,
    SoftwareTrigger,
)
from caqtus.types.expression import Expression


class AnalogSequencerConfiguration(SequencerConfiguration):
    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return (AnalogChannelConfiguration,) * 32


class DigitalSequenceConfiguration(SequencerConfiguration):
    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * 24


configs = {
    "NI6738": AnalogSequencerConfiguration(
        remote_server=None,
        trigger=ExternalClockOnChange(edge=TriggerEdge.RISING),
        channels=(
            AnalogChannelConfiguration(
                description="532 tweezers power (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(
                        lane="532 tweezers \\ power",
                        default=Constant(value=Expression("100 %")),
                    ),
                    input_units=None,
                    output_units="V",
                    measured_data_points=(
                        (0.0, -6.0),
                        (0.07, -5.0),
                        (0.266, -4.0),
                        (0.526, -3.0),
                        (0.772, -2.0),
                        (0.939, -1.0),
                        (1.0, 0.0),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="MOT coils current",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="Coils \\ MOT \\ current", default=None),
                    input_units="A",
                    output_units="V",
                    measured_data_points=((0.0, 0.0), (10.0, 1.67)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="626 MOT frequency",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="626 \\ MOT \\ frequency", default=None),
                    input_units="MHz",
                    output_units="V",
                    measured_data_points=((-20.0, -6.0), (20.0, 6.0)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="421 cell frequency",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="421 cell \\ frequency", default=None),
                    input_units="MHz",
                    output_units="V",
                    measured_data_points=((-40.0, -1.0), (40.0, 1.0)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="Z offset",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="Coils \\ offset \\ Z", default=None),
                    input_units="A",
                    output_units="V",
                    measured_data_points=((-3.0, -10.0), (3.0, 10.0)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="626 MOT power",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="626 \\ MOT \\ power", default=None),
                    input_units="dB",
                    output_units="V",
                    measured_data_points=(
                        (-68.91, 0.0),
                        (-67.94, 1.0),
                        (-54.93, 1.5),
                        (-48.07, 1.6),
                        (-43.4, 1.7),
                        (-33.92, 2.0),
                        (-25.58, 2.5),
                        (-20.78, 3.0),
                        (-14.72, 4.0),
                        (-10.95, 5.0),
                        (-8.03, 6.0),
                        (-5.63, 7.0),
                        (-3.56, 8.0),
                        (-1.68, 9.0),
                        (0.0, 10.0),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="X offset",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="Coils \\ offset \\ X", default=None),
                    input_units="A",
                    output_units="V",
                    measured_data_points=((0.0, 0.0), (6.0, 3.0)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="Y offset",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="Coils \\ offset \\ Y", default=None),
                    input_units="A",
                    output_units="V",
                    measured_data_points=((0.0, 0.0), (6.0, 3.0)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="421 cell power (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(lane="421 cell \\ power", default=None),
                    input_units="dB",
                    output_units="V",
                    measured_data_points=(
                        (-33.63, -0.275),
                        (-30.62, -0.25),
                        (-23.46, -0.225),
                        (-17.66, -0.2),
                        (-13.33, -0.175),
                        (-9.96, -0.15),
                        (-5.18, -0.1),
                        (-2.0, -0.05),
                        (0.0, 0.0),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="push power",
                output=CalibratedAnalogMapping(
                    input_=Constant(value=Expression("mot_loading.push_power")),
                    input_units="mW",
                    output_units="V",
                    measured_data_points=((0.0, 0.05), (0.7, 1.3)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="626 imaging frequency (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(
                        lane="626 imaging \\ frequency",
                        default=Constant(value=Expression("0 MHz")),
                    ),
                    input_units="MHz",
                    output_units="V",
                    measured_data_points=((-20.0, -6.113), (20.0, 6.052)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="626 imaging power (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(
                        lane="626 imaging \\ power",
                        default=Constant(value=Expression("0 dB")),
                    ),
                    input_units="dB",
                    output_units="V",
                    measured_data_points=(
                        (-39.4, 0.5),
                        (-33.0, 0.525),
                        (-26.74, 0.55),
                        (-21.05, 0.575),
                        (-16.0, 0.6),
                        (-11.92, 0.625),
                        (-8.6, 0.65),
                        (-4.03, 0.7),
                        (-1.64, 0.75),
                        (-0.65, 0.8),
                        (0.0, 0.9),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="626 probe frequency ",
                output=CalibratedAnalogMapping(
                    input_=Constant(value=Expression("probe.frequency")),
                    input_units="MHz",
                    output_units="V",
                    measured_data_points=((-20.0, -6.078), (20.0, 6.0453)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="626 probe power",
                output=CalibratedAnalogMapping(
                    input_=Constant(value=Expression("probe.power")),
                    input_units="dB",
                    output_units="V",
                    measured_data_points=(
                        (-44.89, 0.45),
                        (-41.03, 0.465),
                        (-37.45, 0.48),
                        (-32.3, 0.5),
                        (-27.65, 0.52),
                        (-23.17, 0.535),
                        (-19.56, 0.55),
                        (-15.25, 0.57),
                        (-12.72, 0.58),
                        (-8.78, 0.6),
                        (-4.77, 0.625),
                        (-2.05, 0.65),
                        (0.0, 0.7),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="532 lattice power (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(
                        lane="532 lattice \\ power",
                        default=Constant(value=Expression("0")),
                    ),
                    input_units=None,
                    output_units="V",
                    measured_data_points=(
                        (0.02, 0.5),
                        (0.08, 0.55),
                        (0.29, 0.6),
                        (0.69, 0.65),
                        (0.97, 0.7),
                        (1.0, 0.725),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="piezos",
                output=CalibratedAnalogMapping(
                    input_=Constant(value=Expression("0 V")),
                    input_units="V",
                    output_units="V",
                    measured_data_points=((0.0, 0.0), (75.0, 10.0)),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="",
                output=Constant(value=Expression("0 V")),
                output_unit="V",
            ),
        ),
        time_step=Decimal("3000"),
    ),
    "Spincore": DigitalSequenceConfiguration(
        remote_server=None,
        trigger=SoftwareTrigger(),
        channels=(
            DigitalChannelConfiguration(
                description="NI6738 trigger",
                output=DeviceTrigger(device_name="NI6738", default=None),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="2D MOT \\ AOM",
                output=LaneValues(lane="2D MOT \\ AOM", default=None),
            ),
            DigitalChannelConfiguration(
                description="lattice monitoring trigger",
                output=DeviceTrigger(
                    device_name="Fringe stabilizer",
                    default=Constant(value=Expression("Disabled")),
                ),
            ),
            DigitalChannelConfiguration(
                description="741 switch",
                output=LaneValues(
                    lane="741 \\ AOM", default=Constant(value=Expression("Disabled"))
                ),
            ),
            DigitalChannelConfiguration(
                description="oscilloscopes trigger",
                output=Constant(Expression("Disabled")),
            ),
            DigitalChannelConfiguration(
                description="MOT coils",
                output=LaneValues(lane="Coils \\ MOT \\ switch", default=None),
            ),
            DigitalChannelConfiguration(
                description="626 MOT (AOM)",
                output=LaneValues(lane="626 \\ MOT \\ AOM", default=None),
            ),
            DigitalChannelConfiguration(
                description="Push beam (shutter)",
                output=LaneValues(lane="Push beam \\ shutter", default=None),
            ),
            DigitalChannelConfiguration(
                description="421 kill (shutter)",
                output=BroadenLeft(
                    input_=LaneValues(
                        lane="421 cell \\ kill \\ shutter",
                        default=Constant(value=Expression("Disabled")),
                    ),
                    width=Expression("20 ms"),
                ),
            ),
            DigitalChannelConfiguration(
                description="421 horizontal (shutter)",
                output=LaneValues(lane="421 cell \\ horizontal shutter", default=None),
            ),
            DigitalChannelConfiguration(
                description="spectrum dds trigger",
                output=DeviceTrigger(
                    device_name="Spectrum DDS",
                    default=Constant(value=Expression("Disabled")),
                ),
            ),
            DigitalChannelConfiguration(
                description="Orca quest trigger",
                output=DeviceTrigger(
                    device_name="Orca Quest",
                    default=Constant(value=Expression("Disabled")),
                ),
            ),
            DigitalChannelConfiguration(
                description="626 MOT horizontal (shutter)",
                output=LaneValues(
                    lane="626 \\ MOT \\ horizontal shutter", default=None
                ),
            ),
            DigitalChannelConfiguration(
                description="parallel probe shutter",
                output=Constant(value=Expression("parallel_probe")),
            ),
            DigitalChannelConfiguration(
                description="perpendicular probe shutter",
                output=Constant(value=Expression("perp_probe")),
            ),
            DigitalChannelConfiguration(
                description="FSK Siglent 741",
                output=LaneValues(
                    lane="Hop Frequency 741",
                    default=Constant(value=Expression("Disabled")),
                ),
            ),
            DigitalChannelConfiguration(
                description="trigger AWG",
                output=DeviceTrigger(
                    device_name="Tweezer arranger",
                    default=Constant(value=Expression("Disabled")),
                ),
            ),
            DigitalChannelConfiguration(
                description="Swabian pulse streamer trigger",
                output=Constant(Expression("Disabled")),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
        ),
        time_step=Decimal("50"),
    ),
}
