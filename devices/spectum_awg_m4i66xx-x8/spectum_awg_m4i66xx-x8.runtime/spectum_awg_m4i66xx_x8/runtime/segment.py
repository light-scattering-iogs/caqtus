from typing import NewType

import numpy as np

SegmentName = NewType("SegmentName", str)


NumberChannels = NewType("NumberChannels", int)
NumberSamples = NewType("NumberSamples", int)


SegmentData = np.ndarray[tuple[NumberChannels, NumberSamples], np.int16]
