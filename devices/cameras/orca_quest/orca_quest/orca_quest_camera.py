import numpy

from camera import CCamera


class OrcaQuestCamera(CCamera):
    def acquire_picture(self, exposure: float, timeout: float) -> [numpy.ndarray]:
        pass
