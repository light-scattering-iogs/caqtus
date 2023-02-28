from camera.configuration import ROI
from orca_quest.runtime import OrcaQuestCamera

camera = OrcaQuestCamera(
    name="Orca quest",
    camera_number=0,
    picture_names=("picture1", "picture2"),
    exposures=[0.1, 0.2],
    timeout=0.5,
    external_trigger=False,
    roi=ROI(x=0, width=4096, y=0, height=2304),
)

with camera:
    camera.acquire_all_pictures()
