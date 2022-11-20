from multiprocessing.managers import BaseManager


class RemoteDeviceClientManager(BaseManager):
    pass


RemoteDeviceClientManager.register("OrcaQuestCamera")
