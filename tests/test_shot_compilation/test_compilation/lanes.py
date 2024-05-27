from caqtus.types.expression import Expression
from caqtus.types.timelane import (
    TimeLanes,
    DigitalTimeLane,
    AnalogTimeLane,
    Ramp,
    CameraTimeLane,
    TakePicture,
)

lanes = TimeLanes(
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
        "wait",
        "picture",
        "remove atoms",
        "background",
        "fringe",
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
        Expression("5 ms"),
        Expression("imaging.exposure"),
        Expression("30 ms"),
        Expression("imaging.exposure"),
        Expression("200 us"),
        Expression("5 ms"),
        Expression("10 ms"),
    ],
    lanes={
        "Push beam \\ shutter": DigitalTimeLane([True] + [False] * 18 + [True]),
        "2D MOT \\ AOM": DigitalTimeLane([True] + [False] * 18 + [True]),
        "Coils \\ MOT \\ switch": DigitalTimeLane([True] * 5 + [False] * 14 + [True]),
        "Coils \\ MOT \\ current": AnalogTimeLane(
            [Expression("mot_loading.current"), Ramp()]
            + [Expression("red_mot.current")] * 17
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
            + [Expression("imaging.x_current")] * 12
            + [Expression("mot_loading.x_current")]
        ),
        "Coils \\ offset \\ Y": AnalogTimeLane(
            [Expression("mot_loading.y_current"), Ramp()]
            + [Expression("red_mot.y_current")] * 3
            + [Expression("0 A"), Ramp()]
            + [Expression("imaging.y_current")] * 12
            + [Expression("mot_loading.y_current")]
        ),
        "Coils \\ offset \\ Z": AnalogTimeLane(
            [Expression("mot_loading.z_current"), Ramp()]
            + [Expression("red_mot.z_current")] * 3
            + [Expression("-2 A"), Ramp()]
            + [Expression("imaging.z_current")] * 12
            + [Expression("mot_loading.z_current")]
        ),
        "421 cell \\ AOM": DigitalTimeLane([True] + [False] * 18 + [True]),
        "421 cell \\ horizontal shutter": DigitalTimeLane(
            [True] + [False] * 18 + [True]
        ),
        "421 cell \\ kill \\ shutter": DigitalTimeLane([False] * 20),
        "421 cell \\ kill \\ EOM": DigitalTimeLane([False] * 20),
        "421 cell \\ power": AnalogTimeLane(
            [Expression("mot_loading.blue_power")] * 20
        ),
        "421 cell \\ frequency": AnalogTimeLane(
            [Expression("mot_loading.blue_frequency")] * 20
        ),
        "626 \\ MOT \\ AOM": DigitalTimeLane([True] * 5 + [False] * 14 + [True]),
        "626 \\ MOT \\ horizontal shutter": DigitalTimeLane(
            [True] * 5 + [False] * 14 + [True]
        ),
        "626 \\ MOT \\ power": AnalogTimeLane(
            [Expression("mot_loading.red_power"), Ramp()]
            + [Expression("red_mot.power")] * 17
            + [Expression("mot_loading.red_power")]
        ),
        "626 \\ MOT \\ frequency": AnalogTimeLane(
            [Expression("mot_loading.red_frequency"), Ramp()]
            + [Expression("red_mot.frequency")] * 17
            + [Expression("mot_loading.red_frequency")]
        ),
        "Orca Quest": CameraTimeLane(
            [None] * 12
            + [
                TakePicture(picture_name="picture 1"),
                None,
                TakePicture(picture_name="picture 2"),
                None,
                TakePicture(picture_name="background"),
            ]
            + [None] * 3
        ),
        "626 imaging \\ AOM": DigitalTimeLane(
            [False] * 8
            + [True, False, True, False, True, False, True, False, True]
            + [False] * 3
        ),
        "626 imaging \\ frequency": AnalogTimeLane(
            [Expression("collisions.frequency")] * 9
            + [Expression("repump.frequency")] * 2
            + [Expression("imaging.frequency")] * 9
        ),
        "626 imaging \\ power": AnalogTimeLane(
            [Expression("collisions.power")] * 9 + [Expression("imaging.power")] * 11
        ),
        "532 tweezers \\ AOM": DigitalTimeLane(
            [False] * 3 + [True] * 12 + [False, True] + [False] * 2 + [True]
        ),
        "532 tweezers \\ power": AnalogTimeLane(
            [Expression("tweezers.loading_power")] * 7
            + [Ramp()]
            + [Expression("tweezers.imaging_power")] * 11
            + [Expression("100%")]
        ),
        "626 \\ probe \\ AOM": DigitalTimeLane([False] * 20),
    },
)
