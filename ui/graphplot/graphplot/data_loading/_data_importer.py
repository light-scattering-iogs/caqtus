from typing import TypeAlias

from core.data_analysis import ShotData, ShotImporter

DataImporter: TypeAlias = ShotImporter[ShotData]
