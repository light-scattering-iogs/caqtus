import logging
import os
from multiprocessing.managers import BaseManager

from orca_quest.runtime import OrcaQuestCamera

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class RemoteDeviceServerManager(BaseManager):
    pass


RemoteDeviceServerManager.register(
    "OrcaQuestCamera", OrcaQuestCamera, exposed=OrcaQuestCamera.exposed_remote_methods()
)

password = os.environ.get("CAQTUS_DEVICE_SERVER_PASSWORD", None)
if password is None:
    raise ValueError(
        "The environment variable 'CAQTUS_DEVICE_SERVER_PASSWORD' is not set to any value"
    )

manager = RemoteDeviceServerManager(
    address=("", 65000), authkey=bytes(password, encoding="utf-8")
)
server = manager.get_server()
server.serve_forever()
