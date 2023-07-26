import copy
import ctypes
import logging
import math
from collections.abc import Mapping
from typing import ClassVar, Optional

import numpy as np
from pydantic import Field, validator

from device.runtime import RuntimeDevice
from spectum_awg_m4i66xx_x8.configuration import ChannelSettings
from .pyspcm import pyspcm as spcm
from .pyspcm.py_header import spcerr
from .pyspcm.py_header.regs import ERRORTEXTLEN
from .pyspcm.spcm_tools import pvAllocMemPageAligned
from .segment import SegmentData, NumberChannels, SegmentName
from .step import StepConfiguration, StepName

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AMPLITUDE_REGISTERS = (
    spcm.SPC_AMP0,
    spcm.SPC_AMP1,
    spcm.SPC_AMP2,
    spcm.SPC_AMP3,
)


class SpectrumAWGM4i66xxX8(RuntimeDevice):
    """Class to control the Spectrum M4i.66xx.x8 AWG

    Only sequence mode is implemented.

    Fields:
        board_id: An identifier to find the board. ex: /dev/spcm0
        sampling_rate: The sampling rate of the AWG in Hz
        channel_settings: The configuration of the output channels
        segment_names: The names of the segments to split the AWG memory into
    """

    NUMBER_CHANNELS: ClassVar[NumberChannels] = NumberChannels(2)

    board_id: str = Field(
        allow_mutation=False,
    )
    sampling_rate: int = Field(allow_mutation=False)
    channel_settings: tuple[ChannelSettings, ...] = Field(allow_mutation=False)
    segment_names: frozenset[SegmentName] = Field(
        allow_mutation=False,
    )
    first_step: StepName = Field(allow_mutation=False)

    _board_handle: spcm.drv_handle
    _segment_indices: dict[SegmentName, int]
    _steps: dict[StepName, StepConfiguration]
    _step_indices: dict[StepName, int]
    _step_names: dict[int, StepName]
    _bytes_per_sample: int

    def __init__(
        self,
        name: str,
        board_id: str,
        sampling_rate: int,
        channel_settings: tuple[ChannelSettings, ...],
        segment_names: set[SegmentName],
        steps: Mapping[StepName, StepConfiguration],
        first_step: StepName,
    ):
        super().__init__(
            name=name,
            board_id=board_id,
            sampling_rate=sampling_rate,
            channel_settings=channel_settings,
            segment_names=segment_names,
            steps=steps,
            first_step=first_step,
        )
        self._steps = copy.deepcopy(dict(steps))
        self._segment_indices = {
            name: index for index, name in enumerate(self.segment_names)
        }
        self._step_indices = {name: index for index, name in enumerate(self._steps)}
        self._step_names = {index: name for name, index in self._step_indices.items()}

    @validator("channel_settings")
    def validate_channel_settings(cls, channel_settings):
        if len(channel_settings) != cls.NUMBER_CHANNELS:
            raise ValueError(
                f"Expected {cls.NUMBER_CHANNELS} channel settings, but got {len(channel_settings)}"
            )
        return channel_settings

    def initialize(self) -> None:
        """Initialize the AWG.

        This function must be called before any other function.
        """

        super().initialize()
        self._board_handle = spcm.spcm_hOpen(self.board_id)
        if not self._board_handle:
            raise RuntimeError(f"Could not find {self.board_id} board")
        self._add_closing_callback(spcm.spcm_vClose, self._board_handle)

        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_M2CMD, spcm.M2CMD_CARD_RESET
        )
        bytes_per_sample = ctypes.c_int64(-1)
        spcm.spcm_dwGetParam_i64(
            self._board_handle,
            spcm.SPC_MIINST_BYTESPERSAMPLE,
            ctypes.byref(bytes_per_sample),
        )
        self._bytes_per_sample = bytes_per_sample.value
        self.check_error()

        self._setup_channels()
        self._set_sampling_rate(self.sampling_rate)
        self._setup_card_mode()
        self._setup_sequence()
        self._setup_trigger()
        self._enable_output()

    def _setup_channels(self):
        enable = 0
        if self.channel_settings[0].enabled:
            enable |= spcm.CHANNEL0
        if self.channel_settings[1].enabled:
            enable |= spcm.CHANNEL1

        spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_CHENABLE, enable)

        for channel in range(self.NUMBER_CHANNELS):
            channel_name = self.channel_settings[channel].name
            if self.channel_settings[channel].enabled:
                amplitude = int(self.channel_settings[channel].amplitude * 1e3)
                spcm.spcm_dwSetParam_i64(
                    self._board_handle, AMPLITUDE_REGISTERS[channel], amplitude
                )

                set_amplitude = ctypes.c_int64(-1)
                spcm.spcm_dwGetParam_i64(
                    self._board_handle,
                    AMPLITUDE_REGISTERS[channel],
                    ctypes.byref(set_amplitude),
                )
                if set_amplitude.value != amplitude:
                    raise RuntimeError(
                        f"Could not set amplitude of channel {channel_name} to {amplitude} mV"
                    )
                logger.debug(
                    f"Channel {channel_name} amplitude: {set_amplitude.value} mV"
                )
        self.check_error()

    def _set_sampling_rate(self, sampling_rate):
        spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_SAMPLERATE, sampling_rate)

        set_sampling_rate = ctypes.c_int64(-1)
        spcm.spcm_dwGetParam_i64(
            self._board_handle, spcm.SPC_SAMPLERATE, ctypes.byref(set_sampling_rate)
        )

        if set_sampling_rate.value != sampling_rate:
            raise RuntimeError(f"Could not set sampling rate to {sampling_rate} Hz")
        self.check_error()

    def _setup_card_mode(self):
        """Set up the AWG to be in sequence mode with the correct number of segments."""

        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_CARDMODE, spcm.SPC_REP_STD_SEQUENCE
        )

        # The card memory can only be divided by a power of two, so we round up to the next power of two
        number_actual_segments = 2 ** math.ceil(math.log2(len(self.segment_names)))
        if number_actual_segments < 2:
            number_actual_segments = 2
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_MAXSEGMENTS, number_actual_segments
        )
        self.check_error()

    def _setup_sequence(self):
        for step_name, step_config in self._steps.items():
            self._setup_step(step_name, step_config)

        self._set_first_step(self.first_step)

    def _setup_step(self, step_name: StepName, config: StepConfiguration):
        step_index = self._step_indices[step_name]
        segment_index = self._segment_indices[config.segment]
        next_step_index = self._step_indices[config.next_step]

        assert segment_index <= spcm.SPCSEQ_SEGMENTMASK
        assert (next_step_index << 16) <= spcm.SPCSEQ_NEXTSTEPMASK
        mask_lower = segment_index | (next_step_index << 16)

        assert config.repetition <= spcm.SPCSEQ_LOOPMASK
        mask_upper = config.repetition | config.change_condition.value

        mask = mask_lower | (mask_upper << 32)
        spcm.spcm_dwSetParam_i64(
            self._board_handle,
            spcm.SPC_SEQMODE_STEPMEM0 + step_index,
            mask,
        )
        self.check_error()
        logger.debug(f"Setup step {step_name} with {config!r}")

    def _set_first_step(self, first_step: StepName):
        first_step_index = self._step_indices[first_step]

        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_STARTSTEP, first_step_index
        )

    def _setup_trigger(self):
        spcm.spcm_dwSetParam_i64(
            self._board_handle,
            spcm.SPC_TRIG_ORMASK,
            spcm.SPC_TMASK_EXT0,
        )
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_TRIG_EXT0_MODE, spcm.SPC_TM_POS
        )
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_TRIG_TERM, 1
        )  # 50 Ohm termination
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_TRIG_EXT0_ACDC, 1
        )  # DC coupling
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_TRIG_EXT0_LEVEL0, 1000
        )  # 1 V
        self.check_error()

    def _enable_output(self):
        if self.channel_settings[0].enabled:
            spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_ENABLEOUT0, 1)

        if self.channel_settings[1].enabled:
            spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_ENABLEOUT1, 1)

        self.check_error()

    def update_parameters(
        self,
        *,
        segment_data: Optional[Mapping[SegmentName, SegmentData]] = None,
        step_repetitions: Optional[Mapping[StepName, int]] = None,
    ) -> None:
        if segment_data is not None:
            for segment_name, data in segment_data.items():
                self._check_and_write_segment_data(segment_name, data)
        if step_repetitions is not None:
            for step_name, new_repetitions in step_repetitions.items():
                self._steps[step_name].repetition = new_repetitions
                self._setup_step(step_name, self._steps[step_name])

    def _check_and_write_segment_data(
        self,
        segment_name: SegmentName,
        data: SegmentData,
    ):
        data = np.array(data, dtype=np.int16)
        if data.shape[0] != self.number_channels_enabled:
            raise ValueError(
                f"Expected values for {self.number_channels_enabled} channels, but got {data.shape[0]=}"
            )

        if data.shape[1] % 32 != 0:
            raise ValueError(
                f"Expected number of samples to be a multiple of 32, but got {data.shape[1]=}"
            )

        for channel in range(self.number_channels_enabled):
            channel_settings = self.channel_settings[channel]
            power = self._measure_mean_power(data[channel], channel_settings.amplitude)
            power_dbm = 10 * math.log10(power / 1e-3) if power > 0 else -np.inf
            logger.info(
                f"Channel {channel_settings.name} power for segment {segment_name}: {power_dbm:.2f} dBm"
            )
            if power_dbm > channel_settings.maximum_power:
                raise ValueError(
                    f"Power of {power_dbm:.2f} dBm exceeds maximum of "
                    f"{channel_settings.maximum_power:.2f} dBm for channel "
                    f"{channel_settings.name}"
                )

        segment_index = self._get_segment_index(segment_name)
        self._write_segment_data(segment_index, data)
        logger.debug(f"Wrote {data.shape[1]} samples to segment {segment_name}({segment_index})")

    def _get_segment_index(self, segment_name: SegmentName) -> int:
        try:
            return self._segment_indices[segment_name]
        except KeyError:
            raise ValueError(f"There is no segment named {segment_name}")

    @staticmethod
    def _measure_mean_power(data: np.ndarray[np.int16], amplitude: float):
        voltages = data * amplitude / (2**15 - 1)

        output_load = 50  # Ohms

        mean_power = np.mean(voltages**2 / output_load)
        return mean_power

    def _write_segment_data(
        self,
        segment_index: int,
        data: SegmentData,
    ):
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_WRITESEGMENT, segment_index
        )
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_SEGMENTSIZE, data.shape[1]
        )
        self.check_error()

        flattened_data = np.dstack(tuple(data)).flatten(order="C")
        self._transfer_data(flattened_data)


    def _transfer_data(self, data: np.ndarray[np.int16]):
        data_length_bytes = len(data) * self._bytes_per_sample

        buffer = pvAllocMemPageAligned(data_length_bytes)
        ctypes.memmove(buffer, data.ctypes.data, data_length_bytes)

        spcm.spcm_dwDefTransfer_i64(
            self._board_handle,
            spcm.SPCM_BUF_DATA,
            spcm.SPCM_DIR_PCTOCARD,
            0,
            buffer,
            0,
            data_length_bytes,
        )
        spcm.spcm_dwSetParam_i64(
            self._board_handle,
            spcm.SPC_M2CMD,
            spcm.M2CMD_DATA_STARTDMA | spcm.M2CMD_DATA_WAITDMA,
        )
        self.check_error()

        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_M2CMD, spcm.M2CMD_DATA_STOPDMA
        )
        spcm.spcm_dwInvalidateBuf(self._board_handle, spcm.SPCM_BUF_DATA)
        self.check_error()

    def _get_segment_size(self, segment_index: int) -> int:
        """Return the number of samples in the segment."""

        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_WRITESEGMENT, segment_index
        )

        segment_size = ctypes.c_int64(-1)
        spcm.spcm_dwGetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_SEGMENTSIZE, ctypes.byref(segment_size)
        )
        self.check_error()
        return segment_size.value

    def start_sequence(self, external_trigger: bool = False):
        spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_TIMEOUT, 0)
        spcm.spcm_dwSetParam_i64(
            self._board_handle,
            spcm.SPC_M2CMD,
            spcm.M2CMD_CARD_START | spcm.M2CMD_CARD_ENABLETRIGGER,
        )
        if not external_trigger:
            spcm.spcm_dwSetParam_i64(
                self._board_handle, spcm.SPC_M2CMD, spcm.M2CMD_CARD_FORCETRIGGER
            )
        self.check_error()

    def get_current_step(self) -> StepName:
        step_index = ctypes.c_int64(-1)
        spcm.spcm_dwGetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_STATUS, ctypes.byref(step_index)
        )
        self.check_error()
        return self._step_names[step_index.value]

    def stop_sequence(self):
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_M2CMD, spcm.M2CMD_CARD_STOP
        )
        self.check_error()

    def check_error(self):
        buffer = ctypes.create_string_buffer(ERRORTEXTLEN)
        if (
            spcm.spcm_dwGetErrorInfo_i32(self._board_handle, None, None, buffer)
            != spcerr.ERR_OK
        ):
            error_message = bytes(buffer.value).decode("utf-8")
            raise RuntimeError(
                f"An error occurred when programming the board {self.board_id}\n{error_message}"
            )

    def get_maximum_number_segments(self) -> int:
        result = ctypes.c_int64(-1)
        spcm.spcm_dwGetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_AVAILMAXSEGMENT, ctypes.byref(result)
        )
        self.check_error()
        return result.value

    @property
    def number_channels_enabled(self):
        return sum(channel.enabled for channel in self.channel_settings)
