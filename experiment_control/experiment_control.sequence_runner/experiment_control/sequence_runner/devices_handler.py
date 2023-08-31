import asyncio
import logging
from asyncio import TaskGroup
from typing import (
    TYPE_CHECKING,
    Mapping,
)

from attr import define, field

from aod_tweezer_arranger.configuration import AODTweezerArrangerConfiguration
from camera.configuration import CameraConfiguration
from device.configuration import DeviceName
from device.runtime import RuntimeDevice
from experiment.configuration import ExperimentConfig
from sequencer.configuration import SequencerConfiguration
from sequencer.runtime import Sequencer

if TYPE_CHECKING:
    from camera.runtime import Camera
    from aod_tweezer_arranger.runtime import AODTweezerArranger

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@define
class DevicesHandler:
    sequencers: dict[DeviceName, Sequencer] = field(factory=dict)
    cameras: dict[DeviceName, "Camera"] = field(factory=dict)
    tweezer_arrangers: dict[DeviceName, "AODTweezerArranger"] = field(factory=dict)

    async def start_shot(self):
        async with TaskGroup() as g:
            initial_tasks = []
            for tweezer_arrangers in self.tweezer_arrangers.values():
                initial_tasks.append(
                    g.create_task(asyncio.to_thread(tweezer_arrangers.start_sequence))
                )
            for camera in self.cameras.values():
                initial_tasks.append(
                    g.create_task(asyncio.to_thread(camera.start_acquisition))
                )
        # we need the sequencers to be correctly triggered, so we start them in their priority order
        for sequencer in self.sequencers.values():
            sequencer.start_sequence()


def get_sequencers_in_use(
    devices: Mapping[DeviceName, RuntimeDevice], experiment_config: ExperimentConfig
) -> dict[DeviceName, Sequencer]:
    """Return the sequencer devices used in the experiment.

    The sequencers are sorted by trigger priority, with the highest priority first.
    """

    # Here we can't test the type of the runtime device itself because it is actually a proxy and not an instance of
    # the actual device class, that's why we need to test the type of the configuration instead.
    sequencers: dict[DeviceName, Sequencer] = {
        device_name: device
        for device_name, device in devices.items()
        if isinstance(
            experiment_config.get_device_config(device_name),
            SequencerConfiguration,
        )
    }
    sorted_by_trigger_priority = sorted(
        sequencers.items(), key=lambda x: x[1].get_trigger_priority(), reverse=True
    )
    return dict(sorted_by_trigger_priority)


def get_cameras_in_use(
    devices: Mapping[DeviceName, RuntimeDevice], experiment_config: ExperimentConfig
) -> dict[DeviceName, "Camera"]:
    return {
        device_name: device  # type: ignore
        for device_name, device in devices.items()
        if isinstance(
            experiment_config.get_device_config(device_name),
            CameraConfiguration,
        )
    }


def get_tweezer_arrangers_in_use(
    devices: Mapping[DeviceName, RuntimeDevice], experiment_config: ExperimentConfig
) -> dict[DeviceName, "AODTweezerArranger"]:
    return {
        device_name: device  # type: ignore
        for device_name, device in devices.items()
        if isinstance(
            experiment_config.get_device_config(device_name),
            AODTweezerArrangerConfiguration,
        )
    }
