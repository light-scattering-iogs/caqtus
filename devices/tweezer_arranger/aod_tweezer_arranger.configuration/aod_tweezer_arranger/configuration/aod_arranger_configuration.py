from collections.abc import Set, Sequence
from typing import Any

from device.configuration import DeviceParameter
from tweezer_arranger.configuration import (
    TweezerArrangerConfiguration,
    TweezerConfigurationName,
)
from tweezer_arranger_lane.configuration import TweezerAction
from .aod_tweezer_configuration import AODTweezerConfiguration


class AODTweezerArrangerConfiguration(
    TweezerArrangerConfiguration[AODTweezerConfiguration]
):
    awg_board_id: str
    awg_max_power_x: float
    awg_max_power_y: float

    def get_device_type(self) -> str:
        return "AODTweezerArranger"

    def get_device_init_args(
        self,
        tweezer_configurations_to_use: Set[TweezerConfigurationName],
        tweezer_sequencer: Sequence[TweezerAction],
    ) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args(
            tweezer_configurations_to_use, tweezer_sequencer
        ) | {
            "awg_board_id": self.awg_board_id,
            "awg_max_power_x": self.awg_max_power_x,
            "awg_max_power_y": self.awg_max_power_y,
        }
