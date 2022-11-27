from datetime import datetime
from enum import Enum, auto
from typing import Optional

import yaml
from settings_model import SettingsModel


class SequenceState(Enum):
    DRAFT = auto()
    PREPARING = auto()
    RUNNING = auto()
    FINISHED = auto()
    INTERRUPTED = auto()
    CRASHED = auto()
    UNTRUSTED = auto()


def state_representer(dumper: yaml.Dumper, state: SequenceState):
    return dumper.represent_scalar("!SequenceState", state.name)


yaml.SafeDumper.add_representer(SequenceState, state_representer)


def state_constructor(loader: yaml.Loader, node: yaml.Node):
    return SequenceState[loader.construct_scalar(node)]


yaml.SafeLoader.add_constructor(f"!SequenceState", state_constructor)


class SequenceStats(SettingsModel):
    state: SequenceState = SequenceState.DRAFT
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
