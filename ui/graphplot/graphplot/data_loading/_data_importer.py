from typing import Any
from typing import TypeAlias, Mapping

from analyza.loading.importers import ShotImporter

DataImporter: TypeAlias = ShotImporter[Mapping[str, Any]]
