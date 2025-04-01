import os

import numpy as np
from matplotlib import pyplot as plt
from PySide6.QtWidgets import QApplication
from screenshot_output_graph import screenshot_node, screenshot_output

from caqtus.device.sequencer.channel_commands import Constant, LaneValues
from caqtus.device.sequencer.timing import to_time_step
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor.channel_output_editor._constant_node import (
    ConstantNode,
)
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor.channel_output_editor._lane_node import (
    LaneNode,
)
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.types.expression import Expression
from caqtus.types.iteration import StepsConfiguration
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.timelane import AnalogTimeLane, DigitalTimeLane, Ramp, TimeLanes
from doc.source.generate_figures.screen_shot_time_lanes import screenshot_time_lanes


def generate_for_constant():
    output = Constant(Expression("10 V"))
    screenshot_output(output, "images/sequencer_outputs/constant_graph.png")
    node = ConstantNode()
    node.set_value(Expression(""))
    screenshot_node(node, "images/sequencer_outputs/constant_node.png")

    sequence_context = SequenceContext._new(
        {},
        StepsConfiguration.empty(),
        ParameterNamespace.empty(),
        TimeLanes(["step1"], [Expression("2 s")]),
    )
    shot_context = ShotContext(sequence_context, {}, {})

    time_step = 3e3
    series = output.evaluate(to_time_step(time_step), 0, 0, shot_context)

    fig, ax = plt.subplots()

    t = np.arange(0, len(series.values)) * time_step * 1e-9
    ax.step(t, series.values.to_pattern().array, where="post")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Output [V]")
    ax.set_ylim(0, 15)
    ax.grid(True)
    ax.set_xlim(t[0], t[-1])

    plt.savefig(
        "images/sequencer_outputs/constant_plot.png",
        bbox_inches="tight",
    )


def generate_digital_lane():
    time_lanes = TimeLanes(
        ["step 1", "step 3", "step 2", "step 4"],
        [Expression("1 s"), Expression("1 s"), Expression("1 s"), Expression("1 s")],
        {
            "digital lane": DigitalTimeLane(
                [
                    False,
                    Expression("Disabled"),
                    Expression("square_wave(t / 50 ms, 0.2)"),
                    True,
                ]
            )
        },
    )
    screenshot_time_lanes(time_lanes, "images/digital_lane/example.png")


def generate_for_lane():
    node = LaneNode()
    node.set_lane_name("")
    screenshot_node(node, "images/sequencer_outputs/lane_node.png")

    output = LaneValues("lane 1")
    screenshot_output(output, "images/sequencer_outputs/lane_graph.png")

    time_lanes = TimeLanes(
        ["step 1", "step 3", "step 2"],
        [Expression("1 s"), Expression("1 s"), Expression("1 s")],
        {"lane 1": AnalogTimeLane([Expression("1 V"), Ramp(), Expression("2 V")])},
    )
    screenshot_time_lanes(time_lanes, "images/sequencer_outputs/lane_time_lanes.png")

    sequence_context = SequenceContext._new(
        {}, StepsConfiguration.empty(), ParameterNamespace.empty(), time_lanes
    )
    shot_context = ShotContext(sequence_context, {}, {})

    time_step = 3e3
    series = output.evaluate(to_time_step(time_step), 0, 0, shot_context)

    fig, ax = plt.subplots()

    t = np.arange(0, len(series.values)) * time_step * 1e-9
    ax.step(t, series.values.to_pattern().array, where="post")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Output [V]")
    ax.set_ylim(0, 3)
    ax.grid(True)
    ax.set_xlim(t[0], t[-1])

    plt.savefig(
        "images/sequencer_outputs/lane_plot.png",
        bbox_inches="tight",
    )


def generate_figures():
    app = QApplication([])
    os.makedirs("images/sequencer_outputs", exist_ok=True)
    screenshot_output(None, "images/sequencer_outputs/output_node.png")
    generate_for_constant()
    generate_for_lane()
    generate_digital_lane()


if __name__ == "__main__":
    generate_figures()
