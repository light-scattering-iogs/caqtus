import warnings
from typing import Optional

from caqtus.session.sql import PostgreSQLExperimentSessionMaker, PostgreSQLConfig
from ._extension import _extension

_session_maker_config: Optional[PostgreSQLConfig] = None


def configure_storage(backend_config: PostgreSQLConfig):
    global _session_maker_config
    if _session_maker_config is not None:
        warnings.warn("Storage configuration is being overwritten.")
    _session_maker_config = backend_config


def get_session_maker() -> PostgreSQLExperimentSessionMaker:
    if _session_maker_config is None:
        error = RuntimeError("Storage configuration has not been set.")
        error.add_note(
            "Please call `configure_storage` with the appropriate configuration."
        )
        raise error
    session_maker = _extension.create_session_maker(
        PostgreSQLExperimentSessionMaker,
        config=_session_maker_config,
    )
    return session_maker
