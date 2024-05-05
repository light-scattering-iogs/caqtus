from typing import Protocol

from caqtus.gui.condetrol.extension import CondetrolExtensionProtocol


class CaqtusExtensionProtocol(Protocol):
    condetrol_extension: CondetrolExtensionProtocol
