from caqtus.types.expression import Expression
from caqtus.types.timelane import TimeLanes, DigitalTimeLane, AnalogTimeLane, Ramp

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
        "wait",
        "cool",
        "wait",
        "ramp",
        "wait",
        "kill",
        "aom off",
        "nothing",
        "ramp",
        "stabilize field",
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
        Expression("1 ms"),
        Expression("1 ms"),
        Expression("cooling_duration"),
        Expression("5 ms"),
        Expression("1 ms"),
        Expression("duration_741"),
        Expression("kill_time"),
        Expression("200 ns"),
        Expression("100 us"),
        Expression("1 ms"),
        Expression("10 ms"),
        Expression("imaging.exposure"),
        Expression("5 ms"),
        Expression("10 ms"),
    ],
    lanes={
        "Push beam \\ shutter": DigitalTimeLane([True] + [False] * 25 + [True]),
        "2D MOT \\ AOM": DigitalTimeLane([True] + [False] * 25 + [True]),
        "Coils \\ MOT \\ switch": DigitalTimeLane([True] * 5 + [False] * 21 + [True]),
        "Coils \\ MOT \\ current": AnalogTimeLane(
            [Expression("mot_loading.current"), Ramp()]
            + [Expression("red_mot.current")] * 24
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
            + [Expression("imaging.x_current")] * 19
            + [Expression("mot_loading.x_current")]
        ),
        "Coils \\ offset \\ Y": AnalogTimeLane(
            [Expression("mot_loading.y_current"), Ramp()]
            + [Expression("red_mot.y_current")] * 3
            + [Expression("0 A"), Ramp()]
            + [Expression("imaging.y_current")] * 19
            + [Expression("mot_loading.y_current")]
        ),
        "Coils \\ offset \\ Z": AnalogTimeLane(
            [Expression("mot_loading.z_current"), Ramp()]
            + [Expression("red_mot.z_current")] * 3
            + [Expression("-2 A"), Ramp()]
            + [Expression("imaging.z_current")] * 19
            + [Expression("mot_loading.z_current")]
        ),
        "421 cell \\ horizontal shutter": DigitalTimeLane(
            [True] + [False] * 25 + [True]
        ),
        "421 cell \\ kill \\ shutter": DigitalTimeLane(
            [False] * 19 + [True] * 2 + [False] * 6
        ),
        "421 cell \\ power": AnalogTimeLane(
            [Expression("mot_loading.blue_power")] * 14
            + [Expression("kill_power")] * 10
            + [Expression("mot_loading.blue_power")] * 3
        ),
        "421 cell \\ frequency": AnalogTimeLane(
            [Expression("mot_loading.blue_frequency")] * 14
            + [Expression("kill_frequency")] * 10
            + [Expression("mot_loading.blue_frequency")] * 3
        ),
        "626 \\ MOT \\ AOM": DigitalTimeLane([True] * 5 + [False] * 21 + [True]),
        "626 \\ MOT \\ horizontal shutter": DigitalTimeLane(
            [True] * 5 + [False] * 21 + [True]
        ),
        "626 \\ MOT \\ power": AnalogTimeLane(
            [Expression("mot_loading.red_power"), Ramp()]
            + [Expression("red_mot.power")] * 24
            + [Expression("mot_loading.red_power")]
        ),
        "626 \\ MOT \\ frequency": AnalogTimeLane(
            [Expression("mot_loading.red_frequency"), Ramp()]
            + [Expression("red_mot.frequency")] * 24
            + [Expression("mot_loading.red_frequency")]
        ),
        "626 imaging \\ frequency": AnalogTimeLane(
            [Expression("collisions.frequency")] * 9
            + [Expression("repump.frequency")] * 2
            + [Expression("imaging.frequency")] * 16
        ),
        "626 imaging \\ power": AnalogTimeLane(
            [Expression("collisions.power")] * 9 + [Expression("imaging.power")] * 18
        ),
        "532 tweezers \\ power": AnalogTimeLane(
            [Expression("tweezers.loading_power*1.175")] * 7
            + [Ramp()]
            + [Expression("tweezers.imaging_power*1.175")] * 5
            + [Ramp()]
            + [Expression("20 %")] * 8
            + [Ramp()]
            + [Expression("tweezers.imaging_power*1.175")] * 3
            + [Expression("100%")]
        ),
        "741 \\ AOM": DigitalTimeLane(
            [False] * 15 + [True] * 2 + [False, True] + [False] * 8
        ),
    },
)
