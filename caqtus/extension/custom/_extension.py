from ..caqtus_extension import CaqtusExtension
from ..device_extension import DeviceExtension
from ..time_lane_extension import TimeLaneExtension

_extension: CaqtusExtension = CaqtusExtension()


def register_device_extension(device_extension: DeviceExtension) -> None:
    _extension.register_device_extension(device_extension)


def register_time_lane_extension(time_lane_extension: TimeLaneExtension) -> None:
    _extension.register_time_lane_extension(time_lane_extension)
