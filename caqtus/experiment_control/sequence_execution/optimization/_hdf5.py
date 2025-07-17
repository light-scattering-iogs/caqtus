import io
import json
from collections.abc import Mapping, Callable, Iterable
from typing import assert_never

import h5py
import numpy as np

from caqtus.types.data import DataLabel, DataType, Data
from caqtus.types.parameter import ParameterType, Parameter
from caqtus.types.parameter._schema import Boolean, Integer, Float, QuantityType
from caqtus.types.variable_name import DottedVariableName


def create_file(
    file: io.BytesIO,
    parameter_schema: Mapping[DottedVariableName, ParameterType],
    data_schema: Mapping[DataLabel, DataType],
    producer: Iterable[
        tuple[Mapping[DottedVariableName, Parameter], Mapping[DataLabel, Data]]
    ],
):
    with h5py.File(file, "w", libver="latest") as f:
        for parameter_name, parameter_type in parameter_schema.items():
            dset = f.create_dataset(
                f"parameters/{parameter_name}",
                dtype=to_numpy_dtype(parameter_type),
                shape=(0,),
                maxshape=(None,),
            )
            dset.attrs["type"] = parameter_tag(parameter_type)
        for data_label, data_type in data_schema.items():
            dset = f.create_dataset(
                f"data/{data_label}",
                dtype=data_type.to_hdf5_dtype(),
                shape=(0,),
                maxshape=(None,),
            )
            dset.attrs["type"] = json.dumps(data_type.unstructure())
        f.swmr_mode = True
        f.flush()

        for i, (parameters, data) in enumerate(producer):
            for parameter_name, parameter_value in parameters.items():
                parameter_type = parameter_schema[parameter_name]
                dset = f[f"parameters/{parameter_name}"]
                dset.resize((i + 1,))
                dset[i] = parameter_type.to_polars_value(parameter_value)
            for data_label, data_value in data.items():
                data_type = data_schema[data_label]
                dset = f[f"data/{data_label}"]
                dset.resize((i + 1,))
                v = data_type.to_hdf5_value(data_value)
                print(v)
                dset[i] = v
            f.flush()


def to_numpy_dtype(parameter_type: ParameterType) -> np.dtype:
    """Convert a parameter type to a numpy dtype."""

    match parameter_type:
        case Boolean():
            return np.dtype(np.bool)
        case Integer():
            return np.dtype(np.int64)
        case Float():
            return np.dtype(np.float64)
        case QuantityType():
            return np.dtype(np.float64)
        case _:
            assert_never(parameter_type)


def parameter_tag(parameter_type: ParameterType) -> str:
    """Return a tag for the parameter type."""

    match parameter_type:
        case Boolean():
            return "bool"
        case Integer():
            return "int"
        case Float():
            return "float"
        case QuantityType(units=units):
            return ("quantity", format(units, "~"))
        case _:
            assert_never(parameter_type)


def parameter_to_value(parameter_type: ParameterType, value: Parameter) -> np.ndarray:
    """Convert a parameter value to a numpy array."""
    match parameter_type:
        case Boolean():
            return np.array(value, dtype=np.bool)
        case Integer():
            return np.array(value, dtype=np.int64)
        case Float():
            return np.array(value, dtype=np.float64)
        case QuantityType(units=units):
            return np.array(value.to_unit(units).magnitude, dtype=np.float64)
        case _:
            assert_never(parameter_type)
