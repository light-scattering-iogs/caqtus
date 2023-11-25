from typing import TypeAlias

from analyza.loading.importers import ShotImporter
from core.data_loading import ShotData

DataImporter: TypeAlias = ShotImporter[ShotData]
