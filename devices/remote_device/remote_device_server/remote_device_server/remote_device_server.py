import logging
import os
from multiprocessing.managers import BaseManager
from typing import Type

from device import RuntimeDevice

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig()

imported_devices: dict[str, Type[RuntimeDevice]] = {}

try:
    from elliptec_ell14.runtime import ElliptecELL14RotationStage

    imported_devices["ElliptecELL14RotationStage"] = ElliptecELL14RotationStage
    logger.info("ElliptecELL14RotationStage imported")
except Exception:
    logger.info("Did not import ElliptecELL14RotationStage")


try:
    from orca_quest.runtime import OrcaQuestCamera

    imported_devices["OrcaQuestCamera"] = OrcaQuestCamera
    logger.info("OrcaQuestCamera imported")
except Exception:
    logger.info("Did not import OrcaQuestCamera")

try:
    from spincore_sequencer.runtime import SpincorePulseBlaster

    imported_devices["SpincorePulseBlaster"] = SpincorePulseBlaster
    logger.info("SpincorePulseBlaster imported")
except Exception:
    logger.info("Did not import SpincorePulseBlaster")

try:
    from ni6738_analog_card.runtime import NI6738AnalogCard

    imported_devices["NI6738AnalogCard"] = NI6738AnalogCard
    logger.info("NI6738AnalogCard imported")
except Exception:
    logger.info("Did not import NI6738AnalogCard")

try:
    from imaging_source.runtime import ImagingSourceCameraDMK33GR0134

    imported_devices["ImagingSourceCameraDMK33GR0134"] = ImagingSourceCameraDMK33GR0134
    logger.info("ImagingSourceCameraDMK33GR0134 imported")
except Exception:
    logger.info("Did not import ImagingSourceCameraDMK33GR0134")

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class RemoteDeviceServerManager(BaseManager):
    pass


for type_name, device_type in imported_devices.items():
    RemoteDeviceServerManager.register(
        type_name, device_type, exposed=device_type.exposed_remote_methods()
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
