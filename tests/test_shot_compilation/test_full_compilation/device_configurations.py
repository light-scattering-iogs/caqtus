from caqtus.device.sequencer import (
    ExternalClockOnChange,
    TriggerEdge,
    AnalogChannelConfiguration,
    SoftwareTrigger,
    DigitalChannelConfiguration,
    ExternalTriggerStart,
)
from caqtus.device.sequencer.configuration import (
    CalibratedAnalogMapping,
    LaneValues,
    Constant,
    DeviceTrigger,
    Advance,
)
from caqtus.types.expression import Expression
from caqtus.utils.roi import RectangularROI
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from orca_quest.configuration import OrcaQuestCameraConfiguration
from spincore_pulse_blaster.configuration import SpincoreSequencerConfiguration
from swabian_pulse_streamer.configuration import SwabianPulseStreamerConfiguration

device_configurations = {
    "NI6738": NI6738SequencerConfiguration(
        remote_server="James",
        trigger=ExternalClockOnChange(edge=TriggerEdge.RISING),
        device_id="Dev1",
        channels=(
            AnalogChannelConfiguration(
                description="532 tweezers power (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(
                        lane="532 tweezers \\ power", default=Expression("100 %")
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
                        (-33.63, -0.35),
                        (-33.63, -0.3),
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
                        lane="626 imaging \\ frequency", default=Expression("0 MHz")
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
                        lane="626 imaging \\ power", default=Expression("0 dB")
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
                        (-36.4, 0.5),
                        (-23.5, 0.55),
                        (-12.05, 0.6),
                        (-3.9, 0.65),
                        (-0.14, 0.7),
                        (0.0, 0.8),
                    ),
                ),
                output_unit="V",
            ),
            AnalogChannelConfiguration(
                description="532 lattice power (AOM)",
                output=CalibratedAnalogMapping(
                    input_=LaneValues(
                        lane="532 lattice \\ power", default=Expression("0")
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
        time_step=3000,
    ),
    "Orca Quest": OrcaQuestCameraConfiguration(
        remote_server="Elizabeth",
        roi=RectangularROI(
            original_image_size=(4096, 2304), x=1948, width=440, y=848, height=400
        ),
        camera_number=0,
    ),
    "Spincore": SpincoreSequencerConfiguration(
        remote_server="James",
        trigger=SoftwareTrigger(),
        board_number=0,
        channels=(
            DigitalChannelConfiguration(
                description="NI6738 trigger", output=DeviceTrigger(device_name="NI6738")
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="2D MOT \\ AOM",
                output=LaneValues(lane="2D MOT \\ AOM", default=None),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="oscilloscopes trigger",
                output=DeviceTrigger(device_name="Swabian pulse streamer"),
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
                output=LaneValues(
                    lane="421 cell \\ kill \\ shutter", default=Expression("Disabled")
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
                output=DeviceTrigger(device_name="Orca Quest"),
            ),
            DigitalChannelConfiguration(
                description="626 MOT horizontal (shutter)",
                output=LaneValues(
                    lane="626 \\ MOT \\ horizontal shutter", default=None
                ),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="",
                output=LaneValues(
                    lane="421 cell \\ kill \\ EOM", default=Expression("Disabled")
                ),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
            DigitalChannelConfiguration(
                description="Swabian pulse streamer trigger",
                output=DeviceTrigger(device_name="Swabian pulse streamer"),
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
        time_step=50,
    ),
    "Swabian pulse streamer": SwabianPulseStreamerConfiguration(
        remote_server="James",
        time_step=1,
        trigger=ExternalTriggerStart(edge=TriggerEdge.RISING),
        ip_address="192.168.137.119",
        channels=(
            DigitalChannelConfiguration(
                description="",
                output=LaneValues(
                    lane="421 cell \\ kill \\ EOM", default=Expression("Disabled")
                ),
            ),
            DigitalChannelConfiguration(
                description="421 kill (EOM)",
                output=Advance(
                    input_=LaneValues(
                        lane="421 cell \\ kill \\ EOM", default=Expression("Disabled")
                    ),
                    advance=Expression("224 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="421 cell (AOM)",
                output=Advance(
                    input_=LaneValues(lane="421 cell \\ AOM", default=None),
                    advance=Expression("1.1 us"),
                ),
            ),
            DigitalChannelConfiguration(
                description="626 imaging (AOM)",
                output=Advance(
                    input_=LaneValues(
                        lane="626 imaging \\ AOM", default=Expression("Disabled")
                    ),
                    advance=Expression("800 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="626 probe AOM",
                output=Advance(
                    input_=LaneValues(
                        lane="626 \\ probe \\ AOM", default=Expression("Disabled")
                    ),
                    advance=Expression("600 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="532 lattice AOM",
                output=Advance(
                    input_=LaneValues(
                        lane="532 lattice \\ AOM", default=Expression("Disabled")
                    ),
                    advance=Expression("730 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="532 tweezers",
                output=Advance(
                    input_=LaneValues(
                        lane="532 tweezers \\ AOM", default=Expression("Disabled")
                    ),
                    advance=Expression("950 ns"),
                ),
            ),
            DigitalChannelConfiguration(
                description="", output=Constant(value=Expression("Disabled"))
            ),
        ),
    ),
}
