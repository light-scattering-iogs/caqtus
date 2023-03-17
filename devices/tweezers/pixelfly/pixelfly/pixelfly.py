from ctypes import CDLL, c_int, byref, c_int8, c_int16, POINTER, c_void_p
from ctypes.util import find_library
from enum import IntFlag, IntEnum

import numpy

from .pixelfly_error import ErrCodes


class PixelDepth(IntEnum):
    BITS_12 = 12
    BITS_8 = 8


class BinMode(IntEnum):
    BIN_1X = 0
    BIN_2X = 1


class Mode(IntFlag):
    """A camera mode is set by the combination of a trigger mode and an acquisition mode.

    ex: HW_TRIGGER | ASYNC_SHUTTER
    """
    # trigger mode
    HW_TRIGGER = 0
    SW_TRIGGER = 1

    # acquisition mode
    ASYNC_SHUTTER = 0x10
    DOUBLE_SHUTTER = 0x20
    VIDEO_MODE = 0x30
    AUTO_EXPOSURE = 0x40


def load_pixelfly_library() -> CDLL:
    pf_cam_lib = find_library("pf_cam")
    if pf_cam_lib is None:
        raise RuntimeError("Could not find pixelfly shared library pf_cam.\n"
                           "Try to install the pixelfly SDK from "
                           "https://www.pco.de/support/software/scientific-cameras-1/pixelfly-qe/")

    lib = CDLL(pf_cam_lib)
    lib.CHECK_BOARD_AVAILABILITY.argtypes = [c_int]
    lib.CHECK_BOARD_AVAILABILITY.restyps = c_int
    lib.SETMODE.argtypes = [c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int]
    lib.SETMODE.restyps = c_int
    lib.READ_IMAGE.argtypes = [c_int, c_int, c_int, c_void_p, c_int]
    lib.READ_IMAGE.restyps = c_int
    return lib


class PixelflyBoard:
    def __init__(self, board_number: int):
        """Initialize the board driver

        :param board_number: an integer between 0 and 7 to indicate which board to use
        """

        self._lib = load_pixelfly_library()
        if self._lib.CHECK_BOARD_AVAILABILITY(board_number) != ErrCodes.NOERR:
            raise RuntimeError(f"Board {board_number} is not available.")

        self._handle = c_int(0)
        if self._lib.INITBOARD(board_number, byref(self._handle)) != ErrCodes.NOERR:
            raise RuntimeError(f"Could not initialize board {board_number}")

        self._board_number = board_number

    def close(self):
        """Must be called to close the board driver"""
        try:
            self.stop_camera()
        finally:
            if self._lib.CLOSEBOARD(byref(self._handle)) != ErrCodes.NOERR:
                raise RuntimeError(f"An error occurred while closing the board {self._board_number}")

    def start_camera(self):
        """Start the camera

        A new exposure can be initiated with a hardware or software trigger, depending on which mode the camera is set.
        """
        if self._lib.START_CAMERA(self._handle) != ErrCodes.NOERR:
            raise RuntimeError(f"Could not start the camera")

    def stop_camera(self):
        """Stop the camera

        Before setting any of the camera parameters, like binning or gain etc., the camera has to be stopped.
        When this method returns, then the CCD is cleared and ready for setting new parameters or starting new
        exposures.
        """
        if self._lib.STOP_CAMERA(self._handle) != ErrCodes.NOERR:
            raise RuntimeError(f"Could not stop the camera")

    def send_software_trigger(self):
        """Send a single trigger in the software trigger mode

        When the camera is set to async shutter software triggered mode a single image is exposed and readout from the
        camera. When the camera is set to video software triggered mode the camera starts streaming images until the
        camera is stopped.
        """
        if self._lib.TRIGGER_CAMERA(self._handle) != ErrCodes.NOERR:
            raise RuntimeError(f"Could not trigger the camera")

    def set_mode(self, mode: Mode, exp_time: int, hbin: BinMode = BinMode.BIN_1X, vbin: BinMode = BinMode.BIN_1X,
                 gain: bool = False, bit_pix: PixelDepth = PixelDepth.BITS_12, exp_level: int = 0):
        """Sets the parameters of the next exposures

        :param mode: Set the camera operation mode. Not all modes work with all camera types.
        In video mode a stream of exposures is started with the next trigger. If exposure time is shorter than readout
        time the exposure of the actual image is done at the end of the CCD readout of the previous image. If exposure
        time is longer than the readout time the actual exposure is directly following the previous exposure. In all
        other modes only one exposure is released by a hardware or a software trigger. The exposure time starts
        directly after the trigger followed by the readout of the CCD.

        :param exp_level: Only available on cameras with auto-exposure capability. Set the level at which the auto
        exposure mode is stopped. The camera measures the incoming light and stops the exposure if the light exceeds
        the set exposure level. Only valid if mode is set to auto exposure. Can be set between 0 and 200.

        :param exp_time: Set the exposure time of the camera. In video mode the value represents times in ms. In all
        other modes the exposure time is in μs. In video mode, can be set between 1 and 65535. In other modes, can be
        set between 5 and 65535.

        :param hbin: Set the horizontal binning and region of the camera. This setting affects the readout of the
        CCD-Chip. Fewer data is transferred but the readout time is not affected.

        :param vbin: Set the vertical binning. This setting affects the readout of the CCD-Chip. Fewer data is
        transferred and the readout time is decreased.

        :param gain: Set the analog gain of the camera.

        :param bit_pix: Set the bit width of the transferred pixels.
        """

        if self._lib.SETMODE(self._handle, mode, exp_level, exp_time, hbin, vbin, int(gain), 0, bit_pix,
                             0) != ErrCodes.NOERR:
            raise ValueError("Could not set the desired parameters")

    def read_image(self, timeout: int) -> numpy.ndarray:
        """Read the next available image from the camera

        If the camera is set to software triggered mode a trigger command is sent to the camera.
        In ‘Double Shutter’ mode (cf. set_mode) the two images are read as one data set of double height.

        :param timeout: Timeout in ms to wait for image.
        """

        ccd_x_size, ccd_y_size = c_int(), c_int()
        actual_x_size, actual_y_size = c_int(), c_int()
        bit_pix = c_int()
        if self._lib.GETSIZES(self._handle, byref(ccd_y_size), byref(ccd_y_size), byref(actual_x_size),
                              byref(actual_y_size), byref(bit_pix)) != ErrCodes.NOERR:
            raise RuntimeError("An error occurred while reading the image size")

        if bit_pix.value == 12:
            dtype = numpy.uint16
            size = actual_x_size.value * actual_y_size.value * 2
            c_type = c_int16
        elif bit_pix.value == 8:
            dtype = numpy.uint8
            size = actual_x_size.value * actual_y_size.value
            c_type = c_int8
        else:
            raise ValueError(f"Unknown bit format {bit_pix.value}")
        image = numpy.zeros((actual_x_size.value, actual_y_size.value), dtype=dtype, order="F")
        if err := self._lib.READ_IMAGE(self._handle, 0, size, image.ctypes.data_as(POINTER(c_type)),
                                       timeout) != ErrCodes.NOERR:
            raise RuntimeError(f"An error occurred while reading the image")
        return image

    def read_temperature(self) -> float:
        """Returns the actual CCD-temperature

        The temperature range is from -55°C to +125°C.
        """
        temperature = c_int()
        if self._lib.READTEMPERATURE(self._handle, byref(temperature)) != ErrCodes.NOERR:
            raise RuntimeError(f"Could not read the camera temperature")
        return float(temperature.value)
