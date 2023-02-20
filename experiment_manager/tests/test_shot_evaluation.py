import numpy as np

from experiment_manager.compute_shot_parameters import evaluate_expression
from expression import Expression
from sequence.configuration import AnalogLane
from units import ureg
from variable import VariableNamespace


def test_evaluate_expression():
    result = evaluate_expression(
        Expression("x"),
        np.array([1, 2, 3]),
        VariableNamespace(x=1),
        "test_step",
        "test_lane",
    )
    assert np.all(result == np.array([1, 1, 1]))

    result = evaluate_expression(
        Expression("10 MHz"),
        np.array([1, 2, 3]),
        VariableNamespace(x=1),
        "test_step",
        "test_lane",
    )
    assert np.all(result == np.array([10, 10, 10]) * ureg.MHz)

    result = evaluate_expression(
        Expression("x * t / (1 s)"),
        np.array([1, 2, 3]),
        VariableNamespace(x=2 * ureg.kHz),
        "test_step",
        "test_lane",
    )
    assert np.all(result == np.array([2, 4, 6]) * ureg.kHz)