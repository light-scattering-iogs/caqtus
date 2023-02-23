import ctypes

from camera.runtime import CCamera

ic = ctypes.cdll.LoadLibrary("tisgrabber_x64.dll")


class ImagingSourceCamera(CCamera):
    pass
