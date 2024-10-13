from typing import Type

import pytest

from caqtus.device.configuration import DeviceServerName
from caqtus.device.sequencer import (
    DigitalChannelConfiguration,
    AnalogChannelConfiguration,
    SequencerConfiguration,
    ChannelConfiguration,
)
from caqtus.device.sequencer.channel_commands import (
    DeviceTrigger,
    Constant,
    LaneValues,
    CalibratedAnalogMapping,
)
from caqtus.device.sequencer.channel_commands.timing import BroadenLeft, Advance
from caqtus.device.sequencer.timing import to_time_step
from caqtus.device.sequencer.trigger import (
    SoftwareTrigger,
    ExternalClockOnChange,
    TriggerEdge,
    ExternalTriggerStart,
)
from caqtus.shot_compilation import VariableNamespace
from caqtus.types.data import DataLabel
from caqtus.types.expression import Expression
from caqtus.types.image import ImageLabel
from caqtus.types.timelane import (
    TimeLanes,
    DigitalTimeLane,
    AnalogTimeLane,
    Ramp,
    CameraTimeLane,
    TakePicture,
)
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName


@pytest.fixture
def variables():
    v = VariableNamespace()
    v.update(
        {
            DottedVariableName("mot_loading.duration"): 50.0 * Unit("millisecond"),
            DottedVariableName("mot_loading.current"): 2.03 * Unit("ampere"),
            DottedVariableName("mot_loading.x_current"): 0.153 * Unit("ampere"),
            DottedVariableName("mot_loading.y_current"): 0.305 * Unit("ampere"),
            DottedVariableName("mot_loading.z_current"): -0.119 * Unit("ampere"),
            DottedVariableName("mot_loading.blue_power"): 1.0,
            DottedVariableName("mot_loading.blue_frequency"): 23.729
            * Unit("megahertz"),
            DottedVariableName("mot_loading.red_frequency"): -3.0 * Unit("megahertz"),
            DottedVariableName("mot_loading.red_power"): 0.0 * Unit("decibel"),
            DottedVariableName("mot_loading.push_power"): 0.7 * Unit("milliwatt"),
            DottedVariableName("imaging.power"): -28.0 * Unit("decibel"),
            DottedVariableName("imaging.frequency"): -18.23 * Unit("megahertz"),
            DottedVariableName("imaging.exposure"): 30.0 * Unit("millisecond"),
            DottedVariableName("imaging.x_current"): 0.25 * Unit("ampere"),
            DottedVariableName("imaging.y_current"): 4.94 * Unit("ampere"),
            DottedVariableName("imaging.z_current"): 0.183 * Unit("ampere"),
            DottedVariableName("red_mot.ramp_duration"): 100.0 * Unit("millisecond"),
            DottedVariableName("red_mot.x_current"): 0.286 * Unit("ampere"),
            DottedVariableName("red_mot.x_current_1"): 0.27 * Unit("ampere"),
            DottedVariableName("red_mot.x_current_2"): 0.3 * Unit("ampere"),
            DottedVariableName("red_mot.y_current"): 0.105 * Unit("ampere"),
            DottedVariableName("red_mot.z_current"): 0.024 * Unit("ampere"),
            DottedVariableName("red_mot.current"): 0.8 * Unit("ampere"),
            DottedVariableName("red_mot.power"): -36.0 * Unit("decibel"),
            DottedVariableName("red_mot.frequency"): -1.05 * Unit("megahertz"),
            DottedVariableName("red_mot.duration"): 100.0 * Unit("millisecond"),
            DottedVariableName("collisions.power"): -29.0 * Unit("decibel"),
            DottedVariableName("collisions.frequency"): -18.08 * Unit("megahertz"),
            DottedVariableName("collisions.duration"): 30.0 * Unit("millisecond"),
            DottedVariableName("tweezers.loading_power"): 0.45,
            DottedVariableName("tweezers.imaging_power"): 0.42,
            DottedVariableName("tweezers.hwp_angle"): 137.75 * Unit("degree"),
            DottedVariableName("tweezers.rearrangement_duration"): 450.0
            * Unit("microsecond"),
            DottedVariableName("tweezers.move_time"): 600.0 * Unit("microsecond"),
            DottedVariableName("repump.frequency"): -16.65 * Unit("megahertz"),
            DottedVariableName("repump.duration"): 25.0 * Unit("millisecond"),
            DottedVariableName("cooling.frequency"): -18.1 * Unit("megahertz"),
            DottedVariableName("target_fringe_position"): 0.3,
            DottedVariableName("kill_frequency"): 40.0 * Unit("megahertz"),
            DottedVariableName("kill_power"): 1.0,
            DottedVariableName("kill_time"): 150.0 * Unit("nanosecond"),
            DottedVariableName("kill_current"): 4.96 * Unit("ampere"),
            DottedVariableName("probe.frequency"): -18.215 * Unit("megahertz"),
            DottedVariableName("probe.power"): 0.0 * Unit("decibel"),
            DottedVariableName("perp_probe"): False,
            DottedVariableName("parallel_probe"): True,
            DottedVariableName("narrow_probe.frequency"): 0.0 * Unit("megahertz"),
            DottedVariableName("narrow_probe.power"): -1.17 * Unit("volt"),
            DottedVariableName("narrow_probe.frequency2"): 0.0 * Unit("megahertz"),
            DottedVariableName("spacing"): 1.4 * Unit("micrometer"),
            DottedVariableName("red_duration"): 190.0 * Unit("nanosecond"),
            DottedVariableName("rep"): 0,
        }
    )
    return v.dict()


@pytest.fixture
def time_lanes():
    return TimeLanes(
        step_names=[
            "load MOT",
            "ramp MOT",
            "Step 2",
            "red MOT",
            "Step 4",
            "close shutter",
            "ramp currents",
            "ramp traps",
            "collisions",
            "repump start",
            "repump",
            "repump end",
            "picture",
            "ramp",
            "rearrange",
            "wait",
            "picture",
            "open shutter",
            "move",
            "wait",
            "cool",
            "ramp",
            "ramp field",
            "stabilize field",
            "ramp lattice",
            "wait",
            "turn off lattice",
            "pi/2 pulse",
            "kill",
            "close aom",
            "ramp",
            "Step 31",
            "move",
            "ramp field",
            "stabilize field",
            "picture",
            "wait",
            "lattice picture",
            "wait",
            "picture",
            "nothing",
            "stop",
        ],
        step_durations=[
            Expression("mot_loading.duration"),
            Expression("red_mot.ramp_duration"),
            Expression("1 ms"),
            Expression("red_mot.duration"),
            Expression("1 ms"),
            Expression("10 ms"),
            Expression("5 ms"),
            Expression("10 ms"),
            Expression("collisions.duration"),
            Expression("1 ms"),
            Expression("repump.duration"),
            Expression("1 ms"),
            Expression("imaging.exposure"),
            Expression("200 ms"),
            Expression("tweezers.rearrangement_duration"),
            Expression("1 ms"),
            Expression("imaging.exposure"),
            Expression("5 ms"),
            Expression("tweezers.move_time"),
            Expression("500 us"),
            Expression("5 ms"),
            Expression("500 us"),
            Expression("1 ms"),
            Expression("20 ms"),
            Expression("800 us"),
            Expression("800 us"),
            Expression("300 ns"),
            Expression("red_duration"),
            Expression("kill_time"),
            Expression("200 ns"),
            Expression("500 us"),
            Expression("500 us"),
            Expression("tweezers.move_time"),
            Expression("1 ms"),
            Expression("20 ms"),
            Expression("imaging.exposure"),
            Expression("10 ms"),
            Expression("200 us"),
            Expression("10 ms"),
            Expression("imaging.exposure"),
            Expression("5 ms"),
            Expression("10 ms"),
        ],
        lanes={
            "Push beam \\ shutter": DigitalTimeLane([True] + [False] * 40 + [True]),
            "2D MOT \\ AOM": DigitalTimeLane([True] + [False] * 40 + [True]),
            "Coils \\ MOT \\ switch": DigitalTimeLane(
                [True] * 5 + [False] * 36 + [True]
            ),
            "Coils \\ MOT \\ current": AnalogTimeLane(
                [Expression("mot_loading.current"), Ramp()]
                + [Expression("red_mot.current")] * 39
                + [Expression("mot_loading.current")]
            ),
            "Coils \\ offset \\ X": AnalogTimeLane(
                [
                    Expression("mot_loading.x_current"),
                    Ramp(),
                    Expression("red_mot.x_current_1"),
                    Ramp(),
                    Expression("red_mot.x_current_2"),
                    Expression("0 A"),
                    Ramp(),
                ]
                + [Expression("imaging.x_current")] * 15
                + [Ramp()]
                + [Expression("kill_current")] * 10
                + [Ramp()]
                + [Expression("imaging.x_current")] * 7
                + [Expression("mot_loading.x_current")]
            ),
            "Coils \\ offset \\ Y": AnalogTimeLane(
                [Expression("mot_loading.y_current"), Ramp()]
                + [Expression("red_mot.y_current")] * 3
                + [Expression("0 A"), Ramp()]
                + [Expression("imaging.y_current")] * 15
                + [Ramp()]
                + [Expression("0 A")] * 10
                + [Ramp()]
                + [Expression("imaging.y_current")] * 7
                + [Expression("mot_loading.y_current")]
            ),
            "Coils \\ offset \\ Z": AnalogTimeLane(
                [Expression("mot_loading.z_current"), Ramp()]
                + [Expression("red_mot.z_current")] * 3
                + [Expression("-2 A"), Ramp()]
                + [Expression("imaging.z_current")] * 34
                + [Expression("mot_loading.z_current")]
            ),
            "421 cell \\ AOM": DigitalTimeLane(
                [True] + [False] * 27 + [True] * 2 + [False] * 11 + [True]
            ),
            "421 cell \\ horizontal shutter": DigitalTimeLane(
                [True] + [False] * 40 + [True]
            ),
            "421 cell \\ kill \\ shutter": DigitalTimeLane(
                [False] * 28 + [True] * 2 + [False] * 12
            ),
            "421 cell \\ kill \\ EOM": DigitalTimeLane(
                [False] * 28 + [True] + [False] * 13
            ),
            "421 cell \\ power": AnalogTimeLane(
                [Expression("mot_loading.blue_power")] * 23
                + [Expression("kill_power")] * 9
                + [Expression("mot_loading.blue_power")] * 10
            ),
            "421 cell \\ frequency": AnalogTimeLane(
                [Expression("mot_loading.blue_frequency")] * 20
                + [Expression("kill_frequency")] * 13
                + [Expression("mot_loading.blue_frequency")] * 9
            ),
            "626 \\ MOT \\ AOM": DigitalTimeLane([True] * 5 + [False] * 36 + [True]),
            "626 \\ MOT \\ horizontal shutter": DigitalTimeLane(
                [True] * 5 + [False] * 36 + [True]
            ),
            "626 \\ MOT \\ power": AnalogTimeLane(
                [Expression("mot_loading.red_power"), Ramp()]
                + [Expression("red_mot.power")] * 39
                + [Expression("mot_loading.red_power")]
            ),
            "626 \\ MOT \\ frequency": AnalogTimeLane(
                [Expression("mot_loading.red_frequency"), Ramp()]
                + [Expression("red_mot.frequency")] * 39
                + [Expression("mot_loading.red_frequency")]
            ),
            "Orca Quest": CameraTimeLane(
                [None] * 12
                + [TakePicture(picture_name=ImageLabel(DataLabel("picture 0")))]
                + [None] * 3
                + [TakePicture(picture_name=ImageLabel(DataLabel("picture 1")))]
                + [None] * 18
                + [TakePicture(picture_name=ImageLabel(DataLabel("picture 2")))]
                + [None] * 3
                + [TakePicture(picture_name=ImageLabel(DataLabel("picture 3")))]
                + [None] * 2
            ),
            "626 imaging \\ AOM": DigitalTimeLane(
                [False] * 8
                + [True, False, True, False, True]
                + [False] * 3
                + [True]
                + [False] * 3
                + [True]
                + [False] * 14
                + [True]
                + [False] * 3
                + [True]
                + [False] * 2
            ),
            "626 imaging \\ frequency": AnalogTimeLane(
                [Expression("collisions.frequency")] * 9
                + [Expression("repump.frequency")] * 2
                + [Expression("imaging.frequency")] * 9
                + [Expression("cooling.frequency")]
                + [Expression("imaging.frequency")] * 21
            ),
            "626 imaging \\ power": AnalogTimeLane(
                [Expression("collisions.power")] * 9
                + [Expression("imaging.power")] * 33
            ),
            "532 tweezers \\ AOM": DigitalTimeLane(
                [False] * 3 + [True] * 23 + [False] * 4 + [True] * 10 + [False, True]
            ),
            "532 tweezers \\ power": AnalogTimeLane(
                [Expression("tweezers.loading_power")] * 7
                + [Ramp()]
                + [Expression("tweezers.imaging_power")] * 11
                + [Ramp(), Expression("100 %"), Ramp()]
                + [Expression("50 %")] * 8
                + [Ramp()]
                + [Expression("tweezers.imaging_power")] * 10
                + [Expression("100%")]
            ),
            "532 lattice \\ power": AnalogTimeLane(
                [Expression("0%")] * 24
                + [Ramp()]
                + [Expression("100 %")] * 6
                + [Ramp()]
                + [Expression("0%")] * 5
                + [Expression("100 %")]
                + [Expression("0%")] * 4
            ),
            "532 lattice \\ AOM": DigitalTimeLane(
                [False] * 24 + [True] * 2 + [False] * 11 + [True] + [False] * 4
            ),
            "626 \\ probe \\ AOM": DigitalTimeLane(
                [False] * 27 + [True] + [False] * 14
            ),
            "Fringe stabilizer": CameraTimeLane(
                [None] * 37
                + [TakePicture(picture_name=ImageLabel(DataLabel("picture")))]
                + [None] * 4
            ),
        },
    )


class SpincoreSequencerConfiguration(SequencerConfiguration):

    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * 24


@pytest.fixture
def spincore_config():
    return SpincoreSequencerConfiguration(
        remote_server="James",
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
                output=DeviceTrigger(
                    device_name="Swabian pulse streamer", default=None
                ),
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
                description="", output=Constant(value=Expression("Disabled"))
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
                output=DeviceTrigger(
                    device_name="Swabian pulse streamer", default=None
                ),
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
        time_step=to_time_step(50),
    )


class NI6738SequencerConfiguration(SequencerConfiguration):

    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return (AnalogChannelConfiguration,) * 32


@pytest.fixture
def ni6738_configuration():
    return NI6738SequencerConfiguration(
        remote_server="James",
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
                        (-49.0, 0.5),
                        (-36.0, 0.55),
                        (-24.0, 0.6),
                        (-13.0, 0.65),
                        (-6.6, 0.7),
                        (-2.0, 0.8),
                        (-1.0, 0.9),
                        (0.0, 1.0),
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
                        (-44.05, 0.45),
                        (-36.71, 0.48),
                        (-31.83, 0.5),
                        (-26.09, 0.52),
                        (-18.56, 0.55),
                        (-13.87, 0.57),
                        (-7.77, 0.6),
                        (-1.32, 0.65),
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
        time_step=to_time_step(3000),
    )


class SwabianPulseStreamerConfiguration(SequencerConfiguration):

    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * 8


@pytest.fixture
def swabian_configuration():
    return SwabianPulseStreamerConfiguration(
        remote_server=DeviceServerName("James"),
        time_step=to_time_step(1),
        trigger=ExternalTriggerStart(edge=TriggerEdge.RISING),
        channels=(
            DigitalChannelConfiguration(
                description="",
                output=LaneValues(
                    lane="421 cell \\ kill \\ EOM",
                    default=Constant(value=Expression("Disabled")),
                ),
            ),
            DigitalChannelConfiguration(
                description="421 kill (EOM)",
                output=Advance(
                    input_=LaneValues(
                        lane="421 cell \\ kill \\ EOM",
                        default=Constant(value=Expression("Disabled")),
                    ),
                    advance=Expression("224 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="421 cell (AOM)",
                output=Advance(
                    input_=BroadenLeft(
                        input_=LaneValues(lane="421 cell \\ AOM", default=None),
                        width=Expression("200 ns"),
                    ),
                    advance=Expression("1.1 us"),
                ),
            ),
            DigitalChannelConfiguration(
                description="626 imaging (AOM)",
                output=Advance(
                    input_=LaneValues(
                        lane="626 imaging \\ AOM",
                        default=Constant(value=Expression("Disabled")),
                    ),
                    advance=Expression("800 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="626 probe AOM",
                output=Advance(
                    input_=LaneValues(
                        lane="626 \\ probe \\ AOM",
                        default=Constant(value=Expression("Disabled")),
                    ),
                    advance=Expression("675 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="532 lattice AOM",
                output=Advance(
                    input_=LaneValues(
                        lane="532 lattice \\ AOM",
                        default=Constant(value=Expression("Disabled")),
                    ),
                    advance=Expression("730 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="532 tweezers",
                output=Advance(
                    input_=LaneValues(
                        lane="532 tweezers \\ AOM",
                        default=Constant(value=Expression("Disabled")),
                    ),
                    advance=Expression("950 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
        ),
    )
