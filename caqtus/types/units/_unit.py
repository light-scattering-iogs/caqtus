from __future__ import annotations

import pint._typing
import pint.facets
import pint.facets.nonmultiplicative.objects
import pint.facets.numpy.unit

UnitLike = pint._typing.UnitLike


class Unit(
    pint.facets.SystemRegistry.Unit,
    pint.facets.numpy.unit.NumpyUnit,
    pint.facets.nonmultiplicative.objects.NonMultiplicativeUnit,
    pint.facets.plain.PlainUnit,
):
    pass
