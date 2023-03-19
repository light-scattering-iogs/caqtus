import pathlib

from pydantic import Field

from settings_model import SettingsModel


class OptimizerConfiguration(SettingsModel):
    """Contain the configuration of an optimizer."""

    description: str = Field(description="A description of the optimization procedure.")
    script_path: pathlib.Path = Field(
        desciption="The path to the script that will be executed to evaluate the cost function."
    )
    parameters: str = Field(description="Extra parameters to pass to the optimizer script.")
    working_directory: pathlib.Path = Field(description="The directory in which the script will be executed.")
