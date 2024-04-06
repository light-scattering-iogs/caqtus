import pickle

from caqtus.shot_compilation import DefaultShotCompiler
from .variables import variables
from .time_lanes import time_lanes
from .device_configurations import device_configurations


def test(request):
    shot_compiler = DefaultShotCompiler(time_lanes, device_configurations)

    result = shot_compiler.compile_shot(variables)

    with open(request.path.parent / "shot_compiler_result.pkl", "rb") as f:
        expected = pickle.load(f)

    assert result == expected
