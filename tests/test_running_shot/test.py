import anyio

from caqtus.device import DeviceName, DeviceController
from caqtus.experiment_control._shot_handling import ShotEventDispatcher
from tests.fixtures import MockDevice


class ControllerTest0(DeviceController[MockDevice]):
    async def run_shot(self):
        await self.wait_all_devices_ready()


def test_0():
    dispatcher = ShotEventDispatcher({DeviceName("device1"), DeviceName("device2")})

    controller1 = ControllerTest0(DeviceName("device1"), dispatcher)
    controller2 = ControllerTest0(DeviceName("device2"), dispatcher)

    async def run():
        async with anyio.create_task_group() as tg:
            tg.start_soon(controller1.run_shot)
            tg.start_soon(controller2.run_shot)

    anyio.run(run, backend="trio")
