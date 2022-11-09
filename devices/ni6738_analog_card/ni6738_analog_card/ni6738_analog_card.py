from typing import ClassVar

from cdevice import CDevice

from pydantic import Field


class NI6738AnalogCard(CDevice):
    channel_number: ClassVar[int] = 32
