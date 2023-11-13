from atom_detector.configuration import ImagingConfigurationName
from atom_detector_lane.configuration import AtomDetectorLane
from camera_lane.configuration import CameraLane
from device.name import DeviceName
from image_types import ImageLabel
from sequence.configuration import ShotConfiguration
from tweezer_arranger_lane.configuration import TweezerArrangerLane


def find_how_to_analyze_images(
    shot_config: ShotConfiguration,
) -> dict[DeviceName, dict[ImageLabel, dict[DeviceName, ImagingConfigurationName]]]:
    """Find out how to analyze images.

    This function returns a dictionary that maps from a camera name to a dictionary that maps from a picture name to a
    tuple of the name of the device that should analyze the picture and the name of the configuration that should be
    used to analyze the picture.
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
                            image_start
                        ]
    return result


FromImageToDetector = dict[
    tuple[DeviceName, ImageLabel], list[tuple[DeviceName, ImagingConfigurationName]]
]
FromDetectorToArranger = dict[tuple[DeviceName, ImageLabel], tuple[DeviceName, int]]


def find_how_to_rearrange(
    shot_config: ShotConfiguration,
) -> tuple[FromImageToDetector, FromDetectorToArranger]:
    """Find out how to analyze images.

    This function returns a dictionary that maps from a camera name to a dictionary that maps from a picture name to a
    tuple of the name of the device that should analyze the picture and the name of the detector that should be used to
    analyze the picture.
    """
    from_image_to_detector: FromImageToDetector = {}
    from_detector_to_arranger: FromDetectorToArranger = {}

    camera_lanes = shot_config.get_lanes(CameraLane)
    detector_lanes = shot_config.get_lanes(AtomDetectorLane)
    arranger_lanes = shot_config.get_lanes(TweezerArrangerLane)

    for camera_name, camera_lane in camera_lanes.items():
        for image_label, image_start, image_stop in camera_lane.get_picture_spans():
            from_image_to_detector[(DeviceName(camera_name), image_label)] = []
            for detector_name, detector_lane in detector_lanes.items():
                use_detector = (
                    (detector_lane[image_start] is not None)
                    and (detector_lane.start_index(image_start) == image_start)
                    and (detector_lane.end_index(image_start) >= image_stop)
                )
                if use_detector:
                    from_image_to_detector[
                        (DeviceName(camera_name), image_label)
                    ].append((DeviceName(detector_name), detector_lane[image_start]))
                    detector_start = detector_lane.start_index(image_start)
                    detector_stop = detector_lane.end_index(image_start)
                    for arranger_name, arranger_lane in arranger_lanes.items():
                        for (
                            step,
                            rearrange_start,
                            rearrange_stop,
                        ) in arranger_lane.get_rearrangement_steps():
                            if (
                                rearrange_start >= detector_start
                                and rearrange_stop <= detector_stop
                            ):
                                from_detector_to_arranger[
                                    (DeviceName(detector_name), image_label)
                                ] = (DeviceName(arranger_name), step)

    return from_image_to_detector, from_detector_to_arranger
