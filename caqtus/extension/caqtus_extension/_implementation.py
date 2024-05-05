import attrs

from caqtus.gui.condetrol.extension import CondetrolExtension
from ._protocol import CaqtusExtensionProtocol


@attrs.frozen
class CaqtusExtension(CaqtusExtensionProtocol):
    condetrol_extension: CondetrolExtension = attrs.field(factory=CondetrolExtension)
