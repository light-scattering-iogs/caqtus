import pickle

import pytest

from .device_configurations import device_configurations
from .time_lanes import time_lanes
from .variables import variables


@pytest.mark.xfail
def test_0(request):
    shot_compiler = ShotCompiler(time_lanes, device_configurations)

    result = shot_compiler.compile_shot(variables)

    with open(request.path.parent / "shot_compiler_result.pkl", "rb") as f:
        expected = pickle.load(f)

    assert result == expected
