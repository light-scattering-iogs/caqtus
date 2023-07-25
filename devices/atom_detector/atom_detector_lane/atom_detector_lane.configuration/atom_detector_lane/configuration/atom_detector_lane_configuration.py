from typing import Optional

from atom_detector.configuration import ConfigurationName
from lane.configuration import Lane


class AtomDetectorLane(Lane[Optional[ConfigurationName]]):
    def get_imaging_configurations(self) -> set[ConfigurationName]:
        result = set[ConfigurationName]()
        for value, _, _ in self.get_value_spans():
            if value is not None:
                result.add(value)
        return result
