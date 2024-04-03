import importlib.metadata

from ._device import Device


def load_installed_devices() -> dict[str, type[Device]]:
    """Returns the device classes that are installed in the current environment.

    This function uses the entry point mechanism to find all the classes that are
    registered under the group `experiment_control.devices`.

    Returns:
        A dictionary matching the entry point name to the class indicated by the object
        reference in the entry point.
        The class referenced must be a subclass of <Device>.
        It can be an implicit subclass, as long as it has the required methods.

    Raises:
        ValueError: if two entry points are found with the same name.
        TypeError: if one of the class referenced is not a subclass of <Device>.
    """

    result: dict[str, type[Device]] = {}

    discovered_entry_points = importlib.metadata.entry_points(
        group="experiment_control.devices"
    )

    for entry_point in discovered_entry_points:
        if entry_point.name in result:
            raise ValueError(
                f"Device entry point `{entry_point.name}` cannot be used more than "
                f"once."
            )
        loaded = discovered_entry_points[entry_point.name].load()
        if not issubclass(loaded, Device):
            raise TypeError(
                f"Entry point {entry_point.name} doesn't reference a <Device> "
                f"subclass, instead got {loaded}"
            )
        result[entry_point.name] = loaded
    return result
