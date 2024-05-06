import warnings
from typing import Optional

import attrs

from caqtus.session.sql import PostgreSQLExperimentSessionMaker
from ._extension import _extension


@attrs.define
class PostgresSQLConfig:
    username: str
    password: str
    host: str
    port: int
    database: str


_session_maker_config: Optional[PostgresSQLConfig] = None


def configure_storage(backend_config: PostgresSQLConfig):
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
        username=_session_maker_config.username,
        password=_session_maker_config.password,
        database=_session_maker_config.database,
        host=_session_maker_config.host,
        port=_session_maker_config.port,
    )
    return session_maker
