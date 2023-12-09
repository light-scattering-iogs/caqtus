from typing import Optional, Any

from toptica.lasersdk.dlcpro.v3_0_1 import NetworkConnection, DLCpro

from device.runtime import RuntimeDevice
from device.runtime.testable_device import TestableDevice, TestError, TestErrorGroup
from util import attrs


def bounds_converter(bounds: Any) -> tuple[Optional[float], Optional[float]]:
    lower_bound, upper_bound = tuple(bounds)

    lower_bound = float(lower_bound) if lower_bound else None
    upper_bound = float(upper_bound) if upper_bound else None

    if isinstance(lower_bound, float) and isinstance(upper_bound, float):
        if not lower_bound < upper_bound:
            raise ValueError(
                f"Expected a tuple of (lower_bound, upper_bound) with lower_bound<upper_bound, "
                f"got ({lower_bound, upper_bound})"
            )
    return lower_bound, upper_bound


@attrs.define
class TopticaDLCPro(RuntimeDevice, TestableDevice):
    """
    Class to interact with toptica dlc pro lasers.

    This class only implement very basic operations with the laser, such as checking that the output power is correct.

    Fields:
        host: The IP address, DNS hostname, serial number or system label of the device.
        output_power_bounds: The bounds to check for when testing the laser. Values should be in mW.
    """

    host: str = attrs.field(converter=str, on_setattr=attrs.setters.frozen)

    output_power_bounds: tuple[Optional[float], Optional[float]] = attrs.field(
        converter=bounds_converter, on_setattr=attrs.setters.frozen
    )

    _dlc_pro: DLCpro = attrs.field(init=False)

    def initialize(self) -> None:
        super().initialize()

        network_connection = NetworkConnection(self.host)
        self._dlc_pro = DLCpro(network_connection)
        self._enter_context(self._dlc_pro)

    def update_parameters(self, *_, **kwargs) -> None:
        pass

    def run_test(self) -> Optional[TestError]:
        test_errors = []
        if output_power_error := self.check_output_power():
            test_errors.append(output_power_error)
        if lock_error := self.check_locked():
            test_errors.append(lock_error)

        if test_errors:
            return TestErrorGroup(
                f"The following tests failed for {self.get_name()}", test_errors
            )

    def check_output_power(self) -> Optional[TestError]:
        output_power = (
            self._dlc_pro.laser1.power_stabilization.input_channel_value_act.get()
        )

        lower_bound = self.output_power_bounds[0]
        if lower_bound and output_power < lower_bound:
            return TestError(
                f"Output power ({output_power:.1f} mW) is lower than the minimum required power ({lower_bound:.1f} mW)"
            )

        upper_bound = self.output_power_bounds[1]
        if upper_bound and output_power > upper_bound:
            return TestError(
                f"Output power ({output_power:.1f} mW) is higher than the maximum tolerable power "
                f"({upper_bound:.1f} mW)"
            )

        return None

    def check_locked(self) -> Optional[TestError]:
        lock_state = self._dlc_pro.laser1.dl.lock.state_txt.get()

        if lock_state == "Locked":
            return None
        else:
            return TestError(
                f"Diode laser is not locked, currently in state {lock_state}"
            )
