from typing import TypeAlias

from core.data_loading import ShotData, ShotImporter

DataImporter: TypeAlias = ShotImporter[ShotData]
