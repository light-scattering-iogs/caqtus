from typing import Optional

from settings_model import SettingsModel
from .shot import ShotConfiguration
from .steps import SequenceSteps


class SequenceConfig(SettingsModel):
    program: SequenceSteps
    shot_configurations: dict[str, ShotConfiguration]

    def compute_total_number_of_shots(self) -> Optional[int]:
        """Return the total number of shots planned for this sequence

        Returns None if this is unknown.
        """

        return self.program.expected_number_shots()
