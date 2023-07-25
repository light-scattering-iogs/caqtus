from atom_detector.configuration import ImagingConfigurationName
from atom_detector_lane.configuration import AtomDetectorLane
from camera_lane.configuration import CameraLane
from device.name import DeviceName
from image_types import ImageLabel
from sequence.configuration import ShotConfiguration


def find_how_to_analyze_images(
    shot_config: ShotConfiguration,
) -> dict[DeviceName, dict[ImageLabel, dict[DeviceName, ImagingConfigurationName]]]:
    """Find out how to analyze images.

    This function returns a dictionary that maps from a camera name to a dictionary that maps from a picture name to a
    tuple of the name of the device that should analyze the picture and the name of the detector that should be used to
    analyze the picture.
    """
    result: dict[
        DeviceName, dict[ImageLabel, dict[DeviceName, "ImagingConfigurationName"]]
    ] = {}

    detector_lanes = shot_config.get_lanes(AtomDetectorLane)

    for camera_name, camera_lane in shot_config.get_lanes(CameraLane).items():
        result[camera_name] = {}
        for image_label, image_start, image_stop in camera_lane.get_picture_spans():
            result[camera_name][image_label] = {}
            for detector_name, detector_lane in detector_lanes.items():
                if detector_lane[image_start] is not None:
                    if (
                        detector_lane.start_index(image_start) == image_start
                        and detector_lane.end_index(image_start) >= image_stop
                    ):
                        result[camera_name][image_label][detector_name] = detector_lane[
                            image_stop
                        ]
    return result
