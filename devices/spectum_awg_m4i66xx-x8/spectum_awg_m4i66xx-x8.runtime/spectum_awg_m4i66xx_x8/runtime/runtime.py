import ctypes
import logging
import math
from typing import ClassVar

import numpy as np
from device import RuntimeDevice
from pydantic import Field, validator

from settings_model import SettingsModel
from .pyspcm import pyspcm as spcm
from .pyspcm.py_header import spcerr
from .pyspcm.py_header.regs import ERRORTEXTLEN

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SpectrumAWGM4i66xxX8(RuntimeDevice):
    """Class to control the Spectrum M4i.66xx.x8 AWG

    Only sequence mode is implemented.
    """

    NUMBER_CHANNELS: ClassVar[int] = 2

    board_id: str = Field(
        description="An identifier to find the board. ex: /dev/spcm0",
        allow_mutation=False,
    )
    channel_settings: tuple["ChannelSettings", ...] = Field(
        description="The configuration of the output channels", allow_mutation=False
    )
    segments: tuple["Segment", ...] = Field(allow_mutation=False)
    first_step: int = Field(allow_mutation=False)
    sampling_rate: int = Field(allow_mutation=False, units="Hz")

    _board_handle: spcm.drv_handle
    _segment_indices: dict[str, int]
    _bytes_per_sample: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._segment_indices = {
            segment.name: index for index, segment in enumerate(self.segments)
        }

    @validator("channel_settings")
    def validate_channel_settings(cls, channel_settings):
        if len(channel_settings) != cls.NUMBER_CHANNELS:
            raise ValueError(
                f"Expected {cls.NUMBER_CHANNELS} channel settings, but got {len(channel_settings)}"
            )
        return channel_settings

    @validator("segments")
    def validate_segments(cls, segments):
        names = set()
        for segment in segments:
            if segment.name in names:
                raise ValueError(f"Duplicate segment name {segment.name}")
            names.add(segment.name)
        return segments

    def start(self) -> None:
        super().start()
        self._board_handle = spcm.spcm_hOpen(self.board_id)
        if not self._board_handle:
            raise RuntimeError(f"Could not find {self.board_id} board")

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

        AMPLITUDE_REGISTERS = (
            spcm.SPC_AMP0,
            spcm.SPC_AMP1,
            spcm.SPC_AMP2,
            spcm.SPC_AMP3,
        )
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
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_CARDMODE, spcm.SPC_REP_STD_SEQUENCE
        )

        # The card memory can only be divided by a power of two, so we round up to the next power of two
        number_actual_segments = 2 ** math.ceil(math.log2(len(self.segments)))
        if number_actual_segments < 2:
            number_actual_segments = 2
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_MAXSEGMENTS, number_actual_segments
        )
        self.check_error()

    def _setup_sequence(self):
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_STARTSTEP, self.first_step
        )

        step = 0
        segment = 0
        loop_number = 1
        next_segment = segment
        leave_condition = spcm.SPCSEQ_ENDLOOPALWAYS

        mask = (
            segment
            | (next_segment << 16)
            | (loop_number << 32)
            | (leave_condition << 32)
        )

        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_SEQMODE_STEPMEM0 + step, mask
        )

    def _setup_trigger(self):
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_TRIG_ORMASK, spcm.SPC_TMASK_SOFTWARE
        )
        self.check_error()

    def _enable_output(self):
        if self.channel_settings[0].enabled:
            spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_ENABLEOUT0, 1)

        if self.channel_settings[1].enabled:
            spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_ENABLEOUT1, 1)

        self.check_error()

    def write_segment_data(
        self,
        segment_name: str,
        data: np.ndarray[("NUMBER_CHANNELS", "number_samples"), np.int16],
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
            power_dbm = 10 * math.log10(power / 1e-3)
            logger.info(
                f"Channel {channel_settings.name} power for segment {segment_name}: {power_dbm:.2f} dBm"
            )
            if power_dbm > channel_settings.maximum_power:
                raise ValueError(
                    f"Power of {power_dbm:.2f} dBm exceeds maximum of "
                    f"{channel_settings.maximum_power:.2f} dBm for channel "
                    f"{channel_settings.name}"
                )

        segment_index = self._segment_indices[segment_name]
        self._write_segment_data(segment_index, data)

    @staticmethod
    def _measure_mean_power(data: np.ndarray[np.int16], amplitude: float):
        voltages = data * amplitude / (2**15 - 1)

        output_load = 50  # Ohms

        mean_power = np.mean(voltages**2 / output_load)
        return mean_power

    @staticmethod
    def _check_power(data, channel_settings: "ChannelSettings"):
        voltages = data * channel_settings.amplitude / (2**15 - 1)

        output_load = 50  # Ohms
        mean_power = np.mean(voltages**2 / output_load)
        mean_power_dbm = 10 * np.log10(mean_power / 1e-3)

        if mean_power_dbm > channel_settings.maximum_power:
            raise ValueError(
                f"Output RF power ({mean_power_dbm:.1f} dBm) is higher than the set limit ({channel_settings.maximum_power}"
                f" dBm) for channel {channel_settings.name}"
            )

    def _write_segment_data(
        self,
        segment_index: int,
        data: np.ndarray[("NUMBER_CHANNELS", "number_samples"), np.int16],
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

        spcm.spcm_dwDefTransfer_i64(
            self._board_handle,
            spcm.SPCM_BUF_DATA,
            spcm.SPCM_DIR_PCTOCARD,
            data_length_bytes,
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
            0,
            data_length_bytes,
        )
        spcm.spcm_dwSetParam_i64(
            self._board_handle,
            spcm.SPC_M2CMD,
            spcm.M2CMD_DATA_STARTDMA | spcm.M2CMD_DATA_WAITDMA,
        )
        self.check_error()

    def run(self):
        spcm.spcm_dwSetParam_i64(self._board_handle, spcm.SPC_TIMEOUT, 0)
        spcm.spcm_dwSetParam_i64(
            self._board_handle,
            spcm.SPC_M2CMD,
            spcm.M2CMD_CARD_START | spcm.M2CMD_CARD_ENABLETRIGGER,
        )
        self.check_error()

    def stop(self):
        spcm.spcm_dwSetParam_i64(
            self._board_handle, spcm.SPC_M2CMD, spcm.M2CMD_CARD_STOP
        )
        self.check_error()

    def shutdown(self):
        try:
            spcm.spcm_vClose(self._board_handle)
        except Exception as error:
            raise error
        finally:
            super().shutdown()

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


class Segment(SettingsModel):
    name: str = Field(description="The name of the segment", allow_mutation=False)
    default_value: np.int16 = Field(default=np.int16(0), allow_mutation=False)


class ChannelSettings(SettingsModel):
    name: str = Field(description="The name of the channel", allow_mutation=False)
    enabled: bool = Field(allow_mutation=False)
    amplitude: float = Field(
        description="The voltage amplitude of the output when setting the extrema values. ex: at an amplitude of 1 V, "
        "the output can swing between +1 V and -1 V in a 50 Ohm termination.",
        units="V",
        allow_mutation=False,
        ge=80e-3,
        le=2.5,
    )
    maximum_power: float = Field(
        description="Maximum average power per segment.",
        units="dBm",
        allow_mutation=False,
    )


SpectrumAWGM4i66xxX8.update_forward_refs()
