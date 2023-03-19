from typing import Optional

from settings_model import SettingsModel
from .sequence_steps import SequenceSteps, get_all_variable_names
from .shot import ShotConfiguration


class SequenceConfig(SettingsModel):
    program: SequenceSteps
    shot_configurations: dict[str, ShotConfiguration]

    def get_all_variable_names(self) -> set[str]:
        return get_all_variable_names(self.program)

    def compute_total_number_of_shots(self) -> Optional[int]:
        """Return the total number of shots planned for this sequence

        Returns None if this is unknown.
        """

        return self.program.expected_number_shots()
