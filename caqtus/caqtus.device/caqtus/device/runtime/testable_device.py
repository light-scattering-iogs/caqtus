from collections.abc import Mapping
from typing import Protocol, runtime_checkable, Optional

import attrs

from .device import Device


@attrs.frozen
class TestError:
    message: str = attrs.field(converter=str)


@attrs.frozen
class DataTestError:
    data: Mapping[str, float] = attrs.field(
        converter=dict,
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.instance_of(str),
            value_validator=attrs.validators.instance_of(float),
        ),
    )


@attrs.frozen
class TestErrorGroup(TestError):
    results: tuple[TestError, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(TestError)
        ),
    )


@runtime_checkable
class TestableDevice(Device, Protocol):
    """
    Interface that defines a device that can be tested to check it is working properly.

    Instances of this class have a `run_test` method that can be called whenever the device is not running to check that
    the device is working properly.
    """

    def run_test(self) -> Optional[TestError]:
        """Test if a device pass the test.

        It is strongly advised to do the test only by reading data from the device and without changing its state if it
        also a device controlling some channels on the experiment.

        Returns:
            None, if the device is working as expected or a test error containing extra information if the device is not
            working as it should.
        """

        ...


@runtime_checkable
class RecalibratingDevice(TestableDevice, Protocol):
    """Interface for a device that can recalibrate itself if it fails to pass its test."""

    def recalibrate(self, test_error: Optional[TestError]) -> bool:
        """Attempts to recalibrate the device.

        Args:
            test_error: An error that occurred previously. If None is passed, the calibration should perform all the
            actions necessary to put the device back in running order. If a specific test error is passed, the device
            can attempt to fix only this specific error instead of doing all the fix operations.

        Returns:
            True, if the recalibration was successful, False, if it failed.
        """

        ...
