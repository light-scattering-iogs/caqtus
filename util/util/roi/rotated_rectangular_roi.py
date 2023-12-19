from collections.abc import Iterable

import attrs
import numpy as np

from .roi import ROI


@attrs.define
class RotatedRectangularROI(ROI):
    center_x: float = attrs.field(
        converter=float,
        on_setattr=attrs.setters.convert,
    )
    center_y: float = attrs.field(
        converter=float,
        on_setattr=attrs.setters.convert,
    )
    width: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    height: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    angle: float = attrs.field(
        converter=float,
        on_setattr=attrs.setters.convert,
    )

    def get_mask(self) -> np.ndarray:
        x, y = np.mgrid[0 : self.original_width, 0 : self.original_height]

        rotated_x = np.cos(self.angle) * (x - self.center_x) + np.sin(self.angle) * (
            y - self.center_y
        )
        rotated_y = np.cos(self.angle) * (y - self.center_y) - np.sin(self.angle) * (
            x - self.center_x
        )

        mask = np.logical_and(
            np.abs(rotated_x) < self.width / 2, np.abs(rotated_y) < self.height / 2
        )
        return mask

    def get_indices(self) -> tuple[Iterable[int], Iterable[int]]:
        x, y = np.mgrid[0 : self.original_width, 0 : self.original_height]
        mask = self.get_mask()
        return x[mask], y[mask]
