import abc

from caqtus.shot_event_dispatcher import ShotEventDispatcher


class DeviceController(abc.ABC):
    @abc.abstractmethod
    async def run_shot(self, shot_event_dispatcher: ShotEventDispatcher) -> None:
        raise NotImplementedError
