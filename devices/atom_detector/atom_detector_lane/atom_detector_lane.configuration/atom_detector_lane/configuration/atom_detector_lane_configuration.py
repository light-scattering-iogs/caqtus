from typing import Optional

from atom_detector.configuration import ImagingConfigurationName
from lane.configuration import Lane


class AtomDetectorLane(Lane[Optional[ImagingConfigurationName]]):
    def get_imaging_configurations(self) -> set[ImagingConfigurationName]:
        result = set[ImagingConfigurationName]()
        for value, _, _ in self.get_value_spans():
            if value is not None:
                result.add(value)
        return result
