import logging

import numpy as np
from orca_quest_camera import OrcaQuestCamera

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

with OrcaQuestCamera(
    name="Orca Quest camera",
    camera_number=0,
    external_trigger=False,
    picture_names=["pict_0", "pict_1"],
    exposures=[10e-3, 10e-3],
    timeout=1,
) as camera:
    camera.acquire_picture()
    camera.acquire_picture()
    v = camera.read_picture("pict_0")
    logger.debug(np.mean(v))
    v = camera.read_picture("pict_1")
    logger.debug(np.mean(v))
