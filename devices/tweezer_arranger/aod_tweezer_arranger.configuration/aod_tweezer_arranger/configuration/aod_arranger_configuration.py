from collections.abc import Set, Sequence
from typing import Any

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceParameter, DeviceConfigurationAttrs
from settings_model import YAMLSerializable
from tweezer_arranger.configuration import (
    TweezerConfigurationName,
    TweezerArrangerConfiguration,
)
from tweezer_arranger_lane.configuration import TweezerAction
from util import attrs
from .aod_tweezer_configuration import AODTweezerConfiguration


@attrs.define(slots=False)
class AODTweezerArrangerConfiguration(
    DeviceConfigurationAttrs,
    ConfigurationHolder[TweezerConfigurationName, AODTweezerConfiguration],
):
    awg_board_id: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    awg_max_power_x: float = attrs.field(
        converter=float, on_setattr=attrs.setters.convert
    )
    awg_max_power_y: float = attrs.field(
        converter=float, on_setattr=attrs.setters.convert
    )

    def get_device_type(self) -> str:
        return "AODTweezerArranger"

    def get_device_init_args(
        self,
        tweezer_configurations_to_use: Set[TweezerConfigurationName],
        tweezer_sequence: Sequence[TweezerAction],
    ) -> dict[DeviceParameter, Any]:
        return TweezerArrangerConfiguration.get_device_init_args(
            self, tweezer_configurations_to_use, tweezer_sequence
        ) | {
            DeviceParameter("awg_board_id"): self.awg_board_id,
            DeviceParameter("awg_max_power_x"): self.awg_max_power_x,
            DeviceParameter("awg_max_power_y"): self.awg_max_power_y,
        }


YAMLSerializable.register_attrs_class(AODTweezerArrangerConfiguration)
