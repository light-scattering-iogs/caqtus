import pickle

from caqtus.shot_compilation import ShotCompiler
from .device_configurations import device_configurations
from .time_lanes import time_lanes
from .variables import variables


def test(request):
    shot_compiler = ShotCompiler(time_lanes, device_configurations)

    result = shot_compiler.compile_shot(variables)

    with open(request.path.parent / "shot_compiler_result.pkl", "rb") as f:
        expected = pickle.load(f)

    assert result == expected
