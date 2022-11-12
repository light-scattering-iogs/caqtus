import logging
from multiprocessing.managers import BaseManager

from orca_quest import OrcaQuestCamera

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class RemoteDeviceManager(BaseManager):
    pass


RemoteDeviceManager.register(
    "OrcaQuestCamera", OrcaQuestCamera, exposed=OrcaQuestCamera.exposed_remote_methods()
)

manager = RemoteDeviceManager(address=("", 65000), authkey=b"Deardear")
server = manager.get_server()
server.serve_forever()
