from collections.abc import Iterable
from typing import Any
from typing import TypeAlias, Mapping

from analyza.loading.importers import ShotImporter

RowData: TypeAlias = Mapping[str, Any]
ShotData: TypeAlias = Iterable[RowData]
DataImporter: TypeAlias = ShotImporter[ShotData]
