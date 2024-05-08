from typing import TypeAlias

import attrs


class LocalExperimentManagerConfiguration:
    pass


@attrs.define
class RemoteExperimentManagerConfiguration:
    address: str
    port: int
    authkey: str


ExperimentManagerConnection: TypeAlias = (
    LocalExperimentManagerConfiguration | RemoteExperimentManagerConfiguration
)
