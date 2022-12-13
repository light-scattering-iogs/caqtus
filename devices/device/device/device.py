from abc import ABC
from functools import singledispatchmethod
from typing import ClassVar

import pydantic
from pydantic import Field, Extra


class Device(pydantic.BaseModel, ABC):
    """Controlled device base class

    All devices used in the experiment must inherit from this class. A device is defined
    by a list of parameters and predetermined methods to call during the sequence.

    Attributes:
        name: A unique name given to the device. This name is checked when starting the device connection.

    Warnings:
        All device classes subclassed from this class should call parent class start, apply_rt_variables and
    shutdown methods when subclassing them.
    """

    name: str = Field(allow_mutation=False)

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return "start", "apply_rt_variables", "shutdown"

    def start(self) -> None:
        """Initiate the communication to the device

        This methode will be called only once at the beginning of the sequence.
        """
        if self.name in self._devices_already_in_use:
            raise ValueError(f"A device with name {self.name} is already in use")
        else:
            self._devices_already_in_use[self.name] = self
        pass

    def apply_rt_variables(self, /, **kwargs) -> None:
        """Apply per shot variables to the device

        The base methode writes named arguments passed to the device attributes.
        """
        for name, value in kwargs.items():
            setattr(self, name, value)

    def shutdown(self):
        self._devices_already_in_use.pop(self.name, None)

    class Config:
        validate_assignment = True
        use_enum_values = True
        validate_all = True
        keep_untouched = (singledispatchmethod,)
        arbitrary_types_allowed = True
        extra = Extra.allow

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    _devices_already_in_use: ClassVar[dict[str, "Device"]] = {}
