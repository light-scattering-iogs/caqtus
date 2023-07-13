from dataclasses import dataclass


@dataclass(frozen=True)
class CameraInstruction:
    """Instruction to take pictures for a camera.

    fields:
        timeout: Maximum time to wait for the camera to take the picture.
        triggers: list of (trigger_value, start_time, stop_time, durations) that specify when the camera trigger should be active.
    """

    timeout: float
    triggers: list[tuple[bool, float, float, float]]
