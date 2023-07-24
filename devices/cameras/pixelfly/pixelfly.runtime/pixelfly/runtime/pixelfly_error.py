from enum import IntEnum

PCO_NOERROR = 0x00000000
PCO_ERROR_CODE_MASK = 0x00000FFF  # in this bit range the error codes reside
PCO_ERROR_LAYER_MASK = 0x0000F000  # in this bit range the layer codes reside
PCO_ERROR_DEVICE_MASK = 0x00FF0000  # bit range for error devices / sources
PCO_ERROR_RESERVED_MASK = 0x1F000000  # reserved for future use
PCO_ERROR_IS_COMMON = 0x20000000  # indicates error message common to all layers
PCO_ERROR_IS_WARNING = 0x40000000  # indicates a warning
PCO_ERROR_IS_ERROR = 0x80000000  # indicates an error condition


class ErrCodes(IntEnum):
    NOERR = 0

    NOTINIT = -1  # Initialization failed; no camera connected
    TIMEOUT = -2  # Timeout in any function
    WRONGVAL = -3  # Function-call with wrong parameter
    NOPCIDEV = -4  # Cannot locate PCI card
    WRONGOS = -5
    NODRIVER = -6
    IOFAILURE = -7

    INVMODE = -9  # Invalid Camera mode
    NOPCIBIOS = -10  # no PCI Bios found

    DEVICEBUSY = -11  # device is hold by an other process
    DATAERROR = -12  # Error in reading or writing data to board
    NOFUNCTION = -13
    NODMABUF = -14  # cannot allocate DMA buffer
    NORBT = -15  # Online.rbt File not found or load error
    POLLERR = -16  # DMA Timeout
    EVENTERR = -17  # creating Event failed

    CAMERABUSY = -20  # LOAD_COC error (Camera runs Program-Memory)
    OUTRAM = -21  # to many values in COC
    WRONGTEMP = -22  # Camera temperature is out of Normal-Range wrong WINDOWS-Version
    NOMEM = -23  # Buffer de/allocate error
    READOUTRUN = -24  # Readout is running
    NOBUFFLAG = -25  # Set/reset Buffer Flags failed
    BUFINUSE = -26  # buffer is used
    SYSERR = -27  # a call to a windows-function fails
    DMARUN = -28  # try to disturb dma running
    NOFILE = -29  # cannot open file
    REGERR = -30  # error in reading/writing to registry
    NODIALOG = -31  # no open dialog
    WRONGVERS = -32  # need newer called vxd or dll
    WRONGEXTSTAT = -33  # one of extended status bits shows an error
    BOARDMEMERR = -34  # board memory has an error
    WRONGCCD = -35  # function not allowed with this ccdtyp
    DMAERROR = -36  # error in DMA from board to memory
    FILE_READ_ERR = -37  # error while reading from file
    FILE_WRITE_ERR = -38  # error while writing to file

    # Warnings
    NOPIC = 100  # picture-buffer empty
    UNDERPIC = 101  # picture too dark
    OVERPIC = 102  # picture too bright
    VALCHANGE = 103  # values changed in TEST_COC
    STR_SHORT = 104  # tab buffer to short in TEST_COC
    TESTSOFT = 120  # Lattice Testsoftware is loaded


def get_error_text(error: int) -> str:
    index = error & PCO_ERROR_CODE_MASK
    if error == PCO_NOERROR or index == 0:
        return "OK."
    device = error & PCO_ERROR_DEVICE_MASK
    layer = error & PCO_ERROR_LAYER_MASK
