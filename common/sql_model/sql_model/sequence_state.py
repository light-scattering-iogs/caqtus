from enum import Enum


class State(Enum):
    DRAFT = "draft"
    PREPARING = "preparing"
    RUNNING = "running"
    FINISHED = "finished"
    INTERRUPTED = "interrupted"
    CRASHED = "crashed"
