from typing import TypeAlias

from core.data_analysis.loading import ShotData, ShotImporter

DataImporter: TypeAlias = ShotImporter[ShotData]
