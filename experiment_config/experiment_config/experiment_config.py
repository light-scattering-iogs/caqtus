from pathlib import Path

from appdirs import user_data_dir
from pydantic import DirectoryPath, Field
from settings_model import SettingsModel


class ExperimentConfig(SettingsModel):
    data_path: Path = Field(
        default_factory=lambda: Path(user_data_dir("ExperimentControl", "Caqtus"))
        / "data/"
    )
