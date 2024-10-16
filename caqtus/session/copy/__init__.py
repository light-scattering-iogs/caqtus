"""Contains utility functions for copying data between sessions.

All functions defined in this package are independent on the implementation of the
session.
"""

from ._copy import copy_path

__all__ = ["copy_path"]
