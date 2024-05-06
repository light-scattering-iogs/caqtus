from collections.abc import Callable
from typing import Concatenate, ParamSpec, TypeVar

import attrs

from caqtus.device.configuration.serializer import DeviceConfigJSONSerializer
from caqtus.gui.condetrol.extension import CondetrolExtension
from caqtus.session import ExperimentSessionMaker
from caqtus.session.shot.timelane.serializer import TimeLaneSerializer
from caqtus.session.sql._serializer import SerializerProtocol, Serializer
from ._protocol import CaqtusExtensionProtocol
from ..device_extension import DeviceExtension
from ..time_lane_extension import TimeLaneExtension

P = ParamSpec("P")
T = TypeVar("T", bound=ExperimentSessionMaker)


@attrs.frozen
class CaqtusExtension(CaqtusExtensionProtocol):
    condetrol_extension: CondetrolExtension = attrs.field(factory=CondetrolExtension)
    device_configurations_serializer: DeviceConfigJSONSerializer = attrs.field(
        factory=DeviceConfigJSONSerializer
    )
    time_lane_serializer: TimeLaneSerializer = attrs.field(factory=TimeLaneSerializer)

    def register_device_extension(self, device_extension: DeviceExtension) -> None:
        self.condetrol_extension.device_extension.register_device_configuration_editor(
            device_extension.configuration_type, device_extension.editor_type
        )
        self.condetrol_extension.device_extension.register_configuration_factory(
            device_extension.label, device_extension.configuration_factory
        )
        self.device_configurations_serializer.register_device_configuration(
            device_extension.configuration_type,
            device_extension.configuration_dumper,
            device_extension.configuration_loader,
        )

    def register_time_lane_extension(
        self, time_lane_extension: TimeLaneExtension
    ) -> None:
        self.time_lane_serializer.register_time_lane(
            time_lane_extension.lane_type,
            time_lane_extension.dumper,
            time_lane_extension.loader,
            time_lane_extension.type_tag,
        )
        self.condetrol_extension.lane_extension.register_lane_factory(
            time_lane_extension.label, time_lane_extension.lane_factory
        )
        self.condetrol_extension.lane_extension.register_lane_model_factory(
            time_lane_extension.lane_type, time_lane_extension.lane_model_factory
        )

    def create_session_maker(
        self,
        session_maker_type: Callable[Concatenate[SerializerProtocol, P], T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        serializer = Serializer.default()
        serializer.device_configuration_serializer = (
            self.device_configurations_serializer
        )
        serializer.time_lane_serializer = self.time_lane_serializer
        return session_maker_type(serializer, *args, **kwargs)
