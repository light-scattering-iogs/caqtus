from typing import Optional

from caqtus.experiment_control.manager import BoundExperimentManager
from ._session_maker import get_session_maker

_experiment_manager: Optional[BoundExperimentManager] = None


def get_experiment_manager() -> BoundExperimentManager:
    global _experiment_manager
    if _experiment_manager is None:
        _experiment_manager = BoundExperimentManager(
            session_maker=get_session_maker(), device_server_configs={}
        )
    return _experiment_manager
