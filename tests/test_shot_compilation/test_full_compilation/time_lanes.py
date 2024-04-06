from caqtus.session.shot import (
    TimeLanes,
    DigitalTimeLane,
    AnalogTimeLane,
    Ramp,
    CameraTimeLane,
    TakePicture,
)
from caqtus.types.expression import Expression

time_lanes = TimeLanes(
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
        "red light",
        "open aom",
        "kill",
        "close aom",
        "ramp",
        "Step 31",
        "move",
        "ramp field",
        "stabilize field",
        "picture",
        "remove atoms",
        "lattice picture",
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
        Expression("100 ms"),
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
        Expression("500 us"),
        Expression("500 us"),
        Expression("red_duration - 200 ns"),
        Expression("200 ns"),
        Expression("kill_time"),
        Expression("200 ns"),
        Expression("500 us"),
        Expression("500 us"),
        Expression("tweezers.move_time"),
        Expression("1 ms"),
        Expression("20 ms"),
        Expression("imaging.exposure"),
        Expression("30 ms"),
        Expression("200 us"),
        Expression("5 ms"),
        Expression("10 ms"),
    ],
    lanes={
        "Push beam \\ shutter": DigitalTimeLane([True] + [False] * 38 + [True]),
        "2D MOT \\ AOM": DigitalTimeLane([True] + [False] * 38 + [True]),
        "Coils \\ MOT \\ switch": DigitalTimeLane([True] * 5 + [False] * 34 + [True]),
        "Coils \\ MOT \\ current": AnalogTimeLane(
            [Expression("mot_loading.current"), Ramp()]
            + [Expression("red_mot.current")] * 37
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
            + [Expression("imaging.x_current")] * 5
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
            + [Expression("imaging.y_current")] * 5
            + [Expression("mot_loading.y_current")]
        ),
        "Coils \\ offset \\ Z": AnalogTimeLane(
            [Expression("mot_loading.z_current"), Ramp()]
            + [Expression("red_mot.z_current")] * 3
            + [Expression("-2 A"), Ramp()]
            + [Expression("imaging.z_current")] * 32
            + [Expression("mot_loading.z_current")]
        ),
        "421 cell \\ AOM": DigitalTimeLane(
            [True] + [False] * 26 + [True] * 3 + [False] * 9 + [True]
        ),
        "421 cell \\ horizontal shutter": DigitalTimeLane(
            [True] + [False] * 38 + [True]
        ),
        "421 cell \\ kill \\ shutter": DigitalTimeLane(
            [False] * 23 + [True] * 7 + [False] * 10
        ),
        "421 cell \\ kill \\ EOM": DigitalTimeLane(
            [False] * 28 + [True] + [False] * 11
        ),
        "421 cell \\ power": AnalogTimeLane(
            [Expression("mot_loading.blue_power")] * 23
            + [Expression("kill_power")] * 9
            + [Expression("mot_loading.blue_power")] * 8
        ),
        "421 cell \\ frequency": AnalogTimeLane(
            [Expression("mot_loading.blue_frequency")] * 20
            + [Expression("kill_frequency")] * 13
            + [Expression("mot_loading.blue_frequency")] * 7
        ),
        "626 \\ MOT \\ AOM": DigitalTimeLane([True] * 5 + [False] * 34 + [True]),
        "626 \\ MOT \\ horizontal shutter": DigitalTimeLane(
            [True] * 5 + [False] * 34 + [True]
        ),
        "626 \\ MOT \\ power": AnalogTimeLane(
            [Expression("mot_loading.red_power"), Ramp()]
            + [Expression("red_mot.power")] * 37
            + [Expression("mot_loading.red_power")]
        ),
        "626 \\ MOT \\ frequency": AnalogTimeLane(
            [Expression("mot_loading.red_frequency"), Ramp()]
            + [Expression("red_mot.frequency")] * 37
            + [Expression("mot_loading.red_frequency")]
        ),
        "Orca Quest": CameraTimeLane(
            [None] * 12
            + [TakePicture(picture_name="picture 0")]
            + [None] * 3
            + [TakePicture(picture_name="picture 1")]
            + [None] * 18
            + [TakePicture(picture_name="picture 2")]
            + [None] * 4
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
            + [False] * 4
        ),
        "626 imaging \\ frequency": AnalogTimeLane(
            [Expression("collisions.frequency")] * 9
            + [Expression("repump.frequency")] * 2
            + [Expression("imaging.frequency")] * 7
            + [Expression("cooling.frequency")] * 3
            + [Expression("imaging.frequency")] * 19
        ),
        "626 imaging \\ power": AnalogTimeLane([Expression("imaging.power")] * 40),
        "532 tweezers \\ AOM": DigitalTimeLane(
            [False] * 3 + [True] * 23 + [False] * 4 + [True] * 6 + [False] * 3 + [True]
        ),
        "532 tweezers \\ power": AnalogTimeLane(
            [Expression("tweezers.loading_power")] * 7
            + [Ramp()]
            + [Expression("tweezers.imaging_power")] * 11
            + [Ramp(), Expression("100 %"), Ramp()]
            + [Expression("50 %")] * 8
            + [Ramp()]
            + [Expression("tweezers.imaging_power")] * 8
            + [Expression("100%")]
        ),
        "532 lattice \\ power": AnalogTimeLane(
            [Expression("0%")] * 24
            + [Ramp()]
            + [Expression("70 %")] * 6
            + [Ramp()]
            + [Expression("0%")] * 5
            + [Expression("100 %")]
            + [Expression("0%")] * 2
        ),
        "532 lattice \\ AOM": DigitalTimeLane(
            [False] * 24
            + [True] * 2
            + [False] * 4
            + [True] * 2
            + [False] * 5
            + [True]
            + [False] * 2
        ),
        "626 \\ probe \\ AOM": DigitalTimeLane(
            [False] * 26 + [True] * 2 + [False] * 12
        ),
    },
)
