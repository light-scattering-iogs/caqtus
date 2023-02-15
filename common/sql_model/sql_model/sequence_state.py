from enum import Enum


class State(Enum):
    DRAFT = "draft"
    PREPARING = "preparing"
    RUNNING = "running"
    FINISHED = "finished"
    INTERRUPTED = "interrupted"
    CRASHED = "crashed"

    @classmethod
    def is_transition_allowed(cls, old_state: "State", new_state: "State") -> bool:
        return new_state in _ALLOWED_TRANSITIONS[old_state]


_ALLOWED_TRANSITIONS = {
    State.DRAFT: {State.PREPARING},
    State.PREPARING: {State.RUNNING, State.CRASHED},
    State.RUNNING: {State.FINISHED, State.INTERRUPTED, State.CRASHED},
    State.FINISHED: {State.DRAFT},
    State.INTERRUPTED: {State.DRAFT},
    State.CRASHED: {State.DRAFT},
}


class InvalidSequenceStateError(Exception):
    pass
