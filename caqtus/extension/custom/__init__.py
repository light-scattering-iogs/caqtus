"""This module acts as a registry for a custom extension to the caqtus package."""

from caqtus.session import ExperimentSessionMaker
from caqtus.session.sql import PostgreSQLConfig
from .._injector import CaqtusInjector
from ..device_extension import DeviceExtension
from ..time_lane_extension import TimeLaneExtension

_injector = CaqtusInjector()


def register_device_extension(device_extension: DeviceExtension) -> None:
    _injector.register_device_extension(device_extension)


def register_time_lane_extension(time_lane_extension: TimeLaneExtension) -> None:
    _injector.register_time_lane_extension(time_lane_extension)


def configure_storage(backend_config: PostgreSQLConfig) -> None:
    _injector.configure_storage(backend_config)


def get_session_maker() -> ExperimentSessionMaker:
    return _injector.get_session_maker()


def launch_condetrol() -> None:
    _injector.launch_condetrol()


__all__ = [
    "register_device_extension",
    "register_time_lane_extension",
    "configure_storage",
    "get_session_maker",
    "launch_condetrol",
]
