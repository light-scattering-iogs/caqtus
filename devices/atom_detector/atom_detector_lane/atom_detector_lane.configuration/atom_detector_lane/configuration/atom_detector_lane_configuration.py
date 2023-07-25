from typing import Optional

from atom_detector.configuration import ConfigurationName
from lane.configuration import Lane


class AtomDetectorLane(Lane[Optional[ConfigurationName]]):
    pass
