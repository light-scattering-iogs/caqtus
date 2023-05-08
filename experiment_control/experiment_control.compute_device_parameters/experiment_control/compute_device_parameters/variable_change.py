from typing import Any

from device.configuration import DeviceName
from experiment.configuration import (
    ElliptecELL14RotationStageConfiguration,
    DeviceParameter,
)
from experiment.configuration import ExperimentConfig
from units import units, Quantity
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace


def compute_parameters_on_variables_update(
    updated_variables: set[DottedVariableName],
    variables: VariableNamespace,
    experiment_config: ExperimentConfig,
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    """Compute the new parameters to apply to the devices when a variable changes."""

    new_parameters = {}
    ell14_configurations = experiment_config.get_device_configs(
        ElliptecELL14RotationStageConfiguration
    )
    new_parameters.update(
        compute_parameters_for_ell14_devices(
            updated_variables, variables, ell14_configurations
        )
    )
    return new_parameters


def compute_parameters_for_ell14_devices(
    updated_variables: set[DottedVariableName],
    variables: VariableNamespace,
    ell14_configurations: dict[DeviceName, ElliptecELL14RotationStageConfiguration],
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    new_parameters = {}
    for name, ell14_config in ell14_configurations.items():
        new_parameters[name] = compute_parameter_for_ell14_device(
            updated_variables, variables, ell14_config
        )
    return new_parameters


def compute_parameter_for_ell14_device(
    updated_variables: set[DottedVariableName],
    variables: VariableNamespace,
    ell14_config: ElliptecELL14RotationStageConfiguration,
) -> dict[DeviceParameter, Any]:
    new_parameters = {}
    upstream_variables = ell14_config.position.upstream_variables.difference(units)
    if upstream_variables.intersection(updated_variables):
        value = ell14_config.position.evaluate(variables | units)
        if isinstance(value, Quantity):
            value = value.to_base_units().magnitude

        new_parameters["position"] = value
    return new_parameters
