import anyio

from caqtus.device import DeviceName
from caqtus.device.controller import DeviceController
from caqtus.shot_event_dispatcher import ShotEventDispatcher
from tests.fixtures import MockDevice


class ControllerTest0(DeviceController[MockDevice]):
    def __init__(self, device: MockDevice, shot_event_dispatcher: ShotEventDispatcher):
        super().__init__(device, shot_event_dispatcher)

    async def run_shot(self):
        self.signal_ready()
        await self.event_dispatcher.wait_all_devices_ready()


def test_0():
    dispatcher = ShotEventDispatcher({DeviceName("device1"), DeviceName("device2")})

    controller1 = ControllerTest0(MockDevice("device1"), dispatcher)
    controller2 = ControllerTest0(MockDevice("device2"), dispatcher)

    async def run():
        async with anyio.create_task_group() as tg:
            tg.start_soon(controller1.run_shot)
            tg.start_soon(controller2.run_shot)

    anyio.run(run, backend="trio")
