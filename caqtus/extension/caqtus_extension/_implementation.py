import attrs

from caqtus.device.configuration.serializer import DeviceConfigJSONSerializer
from caqtus.gui.condetrol.extension import CondetrolExtension
from caqtus.session.shot.timelane.serializer import TimeLaneSerializer
from ._protocol import CaqtusExtensionProtocol
from ..device_extension import DeviceExtension
from ..time_lane_extension import TimeLaneExtension


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
