import logging

import matplotlib.pyplot as plt
import numpy as np

from orca_quest import OrcaQuestCamera
from camera import ROI

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

with OrcaQuestCamera(
    name="Orca Quest camera",
    camera_number=0,
    external_trigger=False,
    roi=ROI(x=100, width=400, y=0, height=400),
    picture_names=["pict_0", "pict_1"],
    exposures=[10e-3, 10e-3],
    timeout=1,
) as camera:
    logger.debug(camera.list_properties())
    camera.acquire_picture()
    camera.acquire_picture()
    v = camera.read_picture("pict_0")
    logger.debug(v.shape)
    v = camera.read_picture("pict_1")
    logger.debug(v)

logger.debug(np.min(v))
logger.debug(np.max(v))

plt.imshow(v.astype(float), vmin=np.min(v), vmax=np.max(v),cmap="inferno")
plt.colorbar()
plt.show()
