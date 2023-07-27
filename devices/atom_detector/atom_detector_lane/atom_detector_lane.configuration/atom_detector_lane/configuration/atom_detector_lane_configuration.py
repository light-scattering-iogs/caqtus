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

    def get_analysis_spans(self) -> list[tuple[ImagingConfigurationName, int, int]]:
        """Get the spans of the analysis.
        """

        result = []
        for cell_value, start, stop in self.get_value_spans():
            if isinstance(cell_value, ImagingConfigurationName):
                result.append((cell_value, start, stop))
        return result
