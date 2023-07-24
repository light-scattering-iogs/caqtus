from typing import Any

from device.configuration import DeviceParameter
from device.name import DeviceName

from tweezer_arranger.configuration import TweezerArrangerConfiguration
from .aod_tweezer_configuration import AODTweezerConfiguration


class AODTweezerArrangerConfiguration(
    TweezerArrangerConfiguration[AODTweezerConfiguration]
):
    awg_to_use: DeviceName

    def get_device_type(self) -> str:
        return "AODTweezerArranger"

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        raise NotImplementedError
