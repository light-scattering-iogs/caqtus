from typing import TypeAlias

import polars

from analyza.loading.importers import ShotImporter

ShotData: TypeAlias = polars.DataFrame
DataImporter: TypeAlias = ShotImporter[ShotData]
