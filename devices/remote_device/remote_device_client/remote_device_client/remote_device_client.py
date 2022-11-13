from multiprocessing.managers import BaseManager


class RemoteDeviceClientManager(BaseManager):
    pass


RemoteDeviceClientManager.register("OrcaQuestCamera")
# manager = RemoteDeviceManager(address=("192.168.137.4", 65000), authkey=b"Deardear")
# manager.connect()
