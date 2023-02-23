from pprint import pprint

from camera.configuration import ROI
from imaging_source.runtime import ImagingSourceCamera
import matplotlib.pyplot as plt

mot_camera = 'DMK 33GR0134 6120749'
test_camera = 'DMK 33GR0134 32220093'

camera = ImagingSourceCamera(
    name="camera",
    camera_name=mot_camera,
    external_trigger=False,
    picture_names=("picture1",),
    exposures=[0.1],
    timeout=1,
    roi=ROI(x=0, y=0, width=100, height=100),
)

print(ImagingSourceCamera.get_device_names())

with camera:
    camera.save_state_to_file("test.xml")
    camera.acquire_all_pictures()
    images = camera.read_all_pictures()
plt.imshow(images["picture1"])
pprint(images["picture1"])
plt.show()
