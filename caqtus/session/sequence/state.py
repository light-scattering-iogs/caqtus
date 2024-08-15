from __future__ import annotations

from enum import Enum


class State(Enum):
    """Indicate the state of a sequence.

    Each sequence in the experiment session has a state. Only sequences in the DRAFT
    state can have their configuration modified. Only sequences in the RUNNING state
    can have data added to them.

    Attributes:
        DRAFT: The sequence was not started yet and is still being edited. When the
            sequence is passed to the experiment manager, it will transition to the
            PREPARING state.
        PREPARING: The sequence is being prepared to run and is currently acquiring the
            necessary resources and devices. No shot have been scheduled to run yet. The
            sequence cannot be interrupted while it is preparing. If the preparation
            succeeds, the sequence will transition to the RUNNING state. If the
            preparation fails, the sequence will transition to the CRASHED state.
        RUNNING: The sequence is currently running shots. When all shots are completed,
            the sequence will transition to the FINISHED state. If the sequence is
            interrupted, it will transition to the INTERRUPTED state. If an error occurs
            while running the sequence, it will transition to the CRASHED state.
        FINISHED: The sequence was successfully run and all shots were completed.
        INTERRUPTED: The sequence was interrupted by the user before all shots were
        completed.
        CRASHED: An error occurred while running the sequence.

    The states FINISHED, INTERRUPTED and CRASHED are terminal states. Once a sequence is
    in one of these states, the only way to change its state is to erase all associated
    data and reset it back to the DRAFT state.
    """

    DRAFT = "draft"
    PREPARING = "preparing"
    RUNNING = "running"
    FINISHED = "finished"
    INTERRUPTED = "interrupted"
    CRASHED = "crashed"

    @classmethod
    def is_transition_allowed(cls, old_state: State, new_state: State) -> bool:
        return new_state in _ALLOWED_TRANSITIONS[old_state]

    def is_editable(self) -> bool:
        """Indicate if a sequence in this state can be edited."""

        return self in {State.DRAFT}

    def __str__(self):
        return self.value


_ALLOWED_TRANSITIONS = {
    State.DRAFT: {State.PREPARING},
    State.PREPARING: {State.RUNNING, State.CRASHED},
    State.RUNNING: {State.FINISHED, State.INTERRUPTED, State.CRASHED},
    State.FINISHED: {State.DRAFT},
    State.INTERRUPTED: {State.DRAFT},
    State.CRASHED: {State.DRAFT},
}
