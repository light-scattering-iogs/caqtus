"""Contains the main GUI from which user can edit and launch sequences."""

from .condetrol import Condetrol, default_connect_to_experiment_manager
from .main_window import CondetrolMainWindow

__all__ = [
    "Condetrol",
    "CondetrolMainWindow",
    "default_connect_to_experiment_manager",
]
