from pydantic import Field

from settings_model import SettingsModel


class ChannelConfiguration(SettingsModel):
    name: str = Field(description="The name of the channel", allow_mutation=False)
    enabled: bool = Field(allow_mutation=False)
    maximum_power: float = Field(
        description="Maximum average power per segment.",
        units="dBm",
        allow_mutation=False,
    )

