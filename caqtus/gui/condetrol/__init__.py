"""Contains the main GUI from which user can edit and launch sequences."""

from .condetrol import Condetrol, default_connect_to_experiment_manager

__all__ = [
    "Condetrol",
    "default_connect_to_experiment_manager",
]
