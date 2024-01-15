from collections.abc import Mapping
from typing import Protocol, Any

from core.device import DeviceName, DeviceParameter, DeviceConfigurationAttrs
from core.session.shot import TimeLanes
from core.types.data import DataLabel, Data


class ShotRunner(Protocol):
    def __enter__(self):
        """All device initialisation must be done here."""
        ...

    def __exit__(self, exc_type, exc_value, traceback):
        """All device cleanup must be done here."""
        ...

    def run_shot(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ) -> Mapping[DataLabel, Data]:
        """Run the shot."""
        ...


class ShotRunnerFactory(Protocol):
    def __call__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ) -> ShotRunner:
        ...
