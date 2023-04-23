from typing import Any

from experiment.configuration import ElliptecELL14RotationStageConfiguration
from experiment.configuration import ExperimentConfig
from units import units, Quantity
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace


def compute_parameters_on_variable_update(
    updated_variable: DottedVariableName,
    experiment_config: ExperimentConfig,
    variables: VariableNamespace,
) -> dict[str, dict[str, Any]]:
    """Compute the new parameters to apply to the devices when a variable changes."""

    new_parameters = {}
    ell14_configurations = experiment_config.get_device_configs(
        ElliptecELL14RotationStageConfiguration
    )
    new_parameters.update(
        compute_parameters_for_ell14_devices(
            updated_variable, ell14_configurations, variables
        )
    )
    return new_parameters


def compute_parameters_for_ell14_devices(
    updated_variable: DottedVariableName,
    ell14_configurations: dict[str, ElliptecELL14RotationStageConfiguration],
    variables: VariableNamespace,
) -> dict[str, dict[str, Any]]:
    new_parameters = {}
    for name, ell14_config in ell14_configurations.items():
        new_parameters[name] = compute_parameter_for_ell14_device(
            updated_variable, ell14_config, variables
        )
    return new_parameters


def compute_parameter_for_ell14_device(
    updated_variable: DottedVariableName,
    ell14_config: ElliptecELL14RotationStageConfiguration,
    variables: VariableNamespace,
) -> dict[str, Any]:
    new_parameters = {}
    upstream_variables = ell14_config.position.upstream_variables.difference(units)
    if updated_variable in upstream_variables:
        value = ell14_config.position.evaluate(variables | units)
        if isinstance(value, Quantity):
            value = value.to_base_units().magnitude

        new_parameters["position"] = value
    return new_parameters
