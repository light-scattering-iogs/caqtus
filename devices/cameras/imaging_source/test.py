from pprint import pprint

from camera.configuration import ROI
from imaging_source.runtime import ImagingSourceCameraDMK33GR0134
import matplotlib.pyplot as plt

mot_camera = 'DMK 33GR0134 6120749'
test_camera = 'DMK 33GR0134 32220093'

camera = ImagingSourceCameraDMK33GR0134(
    name="camera",
    camera_name=mot_camera,
    format="Y800",
    external_trigger=False,
    picture_names=("picture1",),
    exposures=[0.3],
    timeout=5,
    roi=ROI(x=0, y=0, width=100, height=100),
    gain=2.8
)

camera.initialize()
camera.acquire_all_pictures()
images = camera.read_all_pictures()
camera.shutdown()

plt.imshow(images["picture1"])
pprint(images["picture1"])
plt.show()
