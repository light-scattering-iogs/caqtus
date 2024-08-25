from typing import Protocol

from ._shot_primitives import ShotData, DeviceParameters, ShotParameters


class Instrument(Protocol):
    """The interface for the sequence run instrumentation.

    .. note::

        Since all methods here are synchronous, it is discouraged to perform any
        long-running operations in these methods.
    """

    def after_shot_scheduled(self, shot_parameters: ShotParameters) -> None:
        """Called just after a shot is scheduled.

        Args:
            shot_parameters: The parameters requested for the shot.
        """

        pass

    def before_shot_compiled(self, shot_parameters: ShotParameters) -> None:
        """Called just before a shot is compiled.

        Exception raised in this method will be handled as if they were raised during
        the compilation of the shot.

        Args:
            shot_parameters: The parameters used to compile the shot.
        """

        pass

    def after_shot_compiled(self, device_parameters: DeviceParameters) -> None:
        """Called just after a shot is compiled.

        Exception raised in this method will be handled as if they were raised during
        the compilation of the shot.

        Args:
            device_parameters: The parameters used to compile the shot.
        """

        pass

    def before_shot_started(self, device_parameters: DeviceParameters) -> None:
        """Called just before a shot is started.

        Exception raised in this method will be handled as if they were raised during
        the execution of the shot.

        Args:
            device_parameters: The parameters used to run the shot.
        """

        pass

    def after_shot_finished(self, shot_data: ShotData) -> None:
        """Called just after a shot is finished.

        Exception raised in this method will be handled as if they were raised during
        the execution of the shot.

        Args:
            shot_data: The data produced by the shot.
        """

        pass
