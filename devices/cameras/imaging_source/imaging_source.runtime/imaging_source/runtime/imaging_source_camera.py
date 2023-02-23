"""
Imaging Source camera runtime class.

Note that to import this package, the library tisgrabber_x64.dll must be installed
"""

import ctypes
import os

from pydantic import Field

from camera.runtime import CCamera
from .tisgrabber import declareFunctions, D

tisgrabber_path = (
    os.path.expanduser("~")
    + "\\Documents\\The Imaging Source Europe GmbH\\TIS Grabber DLL\\bin\\x64\\tisgrabber_x64.dll"
)

ic = ctypes.cdll.LoadLibrary(tisgrabber_path)
declareFunctions(ic)

ic.IC_InitLibrary(0)


class ImagingSourceCamera(CCamera):
    camera_name: str = Field(description="The name of the camera", allow_mutation=False)
    @classmethod
    def get_device_counts(cls) -> int:
        return ic.IC_GetDeviceCount()

    @classmethod
    def get_device_names(cls) -> list[str]:
        return [D(ic.IC_GetUniqueNamefromList(i)) for i in range(cls.get_device_counts())]
