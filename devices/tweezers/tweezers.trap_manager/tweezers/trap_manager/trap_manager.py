from pydantic import BaseModel, validator

from spectum_awg_m4i66xx_x8.configuration import SpectrumAWGM4i66xxX8Configuration
from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    StepConfiguration,
    StepChangeCondition,
)
from trap_signal_generator.configuration import StaticTrapConfiguration


class TrapManager(BaseModel):
    awg_config: SpectrumAWGM4i66xxX8Configuration
    initial_traps_config: StaticTrapConfiguration
    target_traps_config: StaticTrapConfiguration

    _awg: "SpectrumAWGM4i66xxX8"

    @validator("initial_traps_config")
    def validate_initial_traps_config(
        cls, initial_traps_config: StaticTrapConfiguration, values
    ):
        awg_config: SpectrumAWGM4i66xxX8Configuration = values["awg_config"]
        if initial_traps_config.sampling_rate != awg_config.sampling_rate:
            raise ValueError(
                "Sampling rate of initial traps must be the same than the sampling rate of the AWG"
            )

    @validator("target_traps")
    def validate_target_traps(
        cls, target_traps_config: StaticTrapConfiguration, values
    ):
        initial_traps_config: StaticTrapConfiguration = values["initial_traps_config"]
        if target_traps_config.number_tones > initial_traps_config.number_tones:
            raise ValueError(
                "Number of target traps must smaller than the number of initial traps"
            )
        if target_traps_config.sampling_rate != initial_traps_config.sampling_rate:
            raise ValueError(
                "Sampling rate of target traps must be the same than the sampling rate of initial traps"
            )
        return target_traps_config

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def start(self):
        segment_names = frozenset(
            ("initial_trap_segment", "moving_trap_segment", "target_trap_segment")
        )
        steps = {
            "initial_trap_step": StepConfiguration(
                segment="initial_trap_segment",
                next_step="moving_trap_step",
                repetition=1,
                change_condition=StepChangeCondition.ALWAYS,
            ),
            "moving_trap_step": StepConfiguration(
                segment="moving_trap_segment",
                next_step="target_trap_step",
                repetition=1,
                change_condition=StepChangeCondition.ALWAYS,
            ),
            "target_trap_step": StepConfiguration(
                segment="target_trap_segment",
                next_step="initial_trap_step",
                repetition=1,
                change_condition=StepChangeCondition.ALWAYS,
            ),
        }
        self._awg = SpectrumAWGM4i66xxX8(
            name=self.awg_config.device_name,
            board_id=self.awg_config.board_id,
            sampling_rate=self.awg_config.sampling_rate,
            channel_settings=self.awg_config.channel_settings,
            segment_names=segment_names,
            steps=steps,
            first_step="initial_trap_step",
        )
        self._awg.initialize()

    def stop(self):
        self._awg.stop()

    def shutdown(self):
        self._awg.close()
