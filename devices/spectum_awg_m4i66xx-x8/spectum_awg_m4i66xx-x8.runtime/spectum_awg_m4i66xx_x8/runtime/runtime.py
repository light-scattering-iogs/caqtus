from device import RuntimeDevice
from pydantic import Field
import ctypes

from .pyspcm import pyspcm as spcm


class SpectrumAWGM4i66xxX8(RuntimeDevice):
    board_id: str = Field(
        description="An identifier to find the board. ex: /dev/spcm0",
        allow_mutation=False,
    )

    _board_handle: spcm.drv_handle

    def start(self) -> None:
        super().start()
        self._board_handle = spcm.spcm_hOpen(ctypes.c_wchar_p(self.board_id))

    def shutdown(self):
        try:
            spcm.spcm_vClose(self._board_handle)
        except Exception as error:
            raise error
        finally:
            super().shutdown()
