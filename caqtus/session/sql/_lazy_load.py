import logging
from collections.abc import Iterator, Mapping
from typing import assert_never

import attrs
import numpy as np
import polars
from polars.io.plugins import register_io_source
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased
from tqdm.auto import tqdm

from caqtus.types.data import DataType, Data
from caqtus.types.parameter import Parameter, ParameterType, converter
from caqtus.types.units import Quantity
from ._sequence_table import SQLSequence
from ._shot_tables import SQLShot, SQLShotParameter, SQLShotArray, SQLStructuredShotData

logger = logging.getLogger(__name__)

structure_parameter = converter.get_structure_hook(bool | int | float | Quantity)


@attrs.frozen
class RestrictedLoader:
    session: Session
    sequence_model: SQLSequence
    number_shots: int
    batch_size: int
    metadata_schema: dict[str, polars.DataType]
    parameter_schema: Mapping[str, ParameterType]
    data_schema: Mapping[str, DataType]

    def __call__(self) -> Iterator[polars.DataFrame]:
        sequence_name = self.sequence_model.path.path

        pl_parameter_schema = get_parameter_pl_schema(self.parameter_schema)
        pl_data_schema = {
            column: data_type.to_polars_dtype()
            for column, data_type in self.data_schema.items()
        }
        shots_query = self.build_query()
        for shot, parameters, *data in tqdm(
            self.session.execute(shots_query).tuples(), total=self.number_shots
        ):
            shot_metadata = {}
            if "sequence" in self.metadata_schema:
                shot_metadata["sequence"] = (sequence_name,)
            if "shot_index" in self.metadata_schema:
                shot_metadata["shot_index"] = (shot.index,)
            if "shot_start_time" in self.metadata_schema:
                shot_metadata["shot_start_time"] = (shot.start_time,)
            if "shot_end_time" in self.metadata_schema:
                shot_metadata["shot_end_time"] = (shot.end_time,)
            metadata_df = polars.DataFrame(shot_metadata, schema=self.metadata_schema)

            shot_parameters = {}
            for parameter_name, parameter_type in self.parameter_schema.items():
                parameter_value = structure_parameter(
                    parameters.content[parameter_name], Parameter
                )
                shot_parameters[parameter_name] = (
                    parameter_type.to_polars_value(parameter_value),
                )
            parameter_df = polars.DataFrame(shot_parameters, schema=pl_parameter_schema)

            pl_data = {}
            for raw_model, (data_name, data_type) in zip(
                data, self.data_schema.items(), strict=True
            ):
                saved_value = structure_shot_sql_data(raw_model)
                pl_data[data_name] = (data_type.to_polars_value(saved_value),)
            data_df = polars.DataFrame(pl_data, schema=pl_data_schema)

            df = polars.concat([metadata_df, parameter_df, data_df], how="horizontal")

            yield df

    def build_query(self):
        aliased_data = {
            data_name: aliased(
                SQLShotArray if data_type.is_saved_as_array() else SQLStructuredShotData
            )
            for data_name, data_type in self.data_schema.items()
        }

        shots_query = (
            select(SQLShot, SQLShotParameter, *aliased_data.values())
            .where(
                SQLShot.sequence == self.sequence_model,
                SQLShot.index < self.number_shots,
            )
            .join(SQLShotParameter)
        )
        for data_name, aliased_table in aliased_data.items():
            shots_query = shots_query.join(
                aliased_table, SQLShot.id_ == aliased_table.shot_id
            ).where(aliased_table.label == data_name)
        shots_query = shots_query.order_by(SQLShot.index).execution_options(
            yield_per=self.batch_size
        )
        return shots_query


def scan(
    session: Session,
    sequence: SQLSequence,
    parameter_schema: Mapping[str, ParameterType],
    data_schema: Mapping[str, DataType],
) -> polars.LazyFrame:
    pl_shot_metadata_schema = get_shot_metadata_pl_schema()
    pl_parameter_schema = get_parameter_pl_schema(parameter_schema)
    pl_data_schema = {
        column: data_type.to_polars_dtype() for column, data_type in data_schema.items()
    }
    pl_schema = pl_shot_metadata_schema | pl_parameter_schema | pl_data_schema

    def load(
        with_columns: list[str] | None,
        predicate: polars.Expr | None,
        n_rows: int | None,
        batch_size: int | None,
    ) -> Iterator[polars.DataFrame]:
        if with_columns is None:
            restricted_metadata_schema = pl_shot_metadata_schema
            restricted_parameter_schema = parameter_schema
            restricted_data_schema = data_schema
        else:
            restricted_metadata_schema = {
                column: pl_shot_metadata_schema[column]
                for column in with_columns
                if column in pl_shot_metadata_schema
            }
            restricted_parameter_schema = {
                column: parameter_type
                for column, parameter_type in parameter_schema.items()
                if column in with_columns
            }
            restricted_data_schema = {
                column: data_type
                for column, data_type in data_schema.items()
                if column in with_columns
            }
        if n_rows is None:
            number_shots_to_load = sequence.number_shots()
        else:
            number_shots_to_load = min(n_rows, sequence.number_shots())
        if batch_size is None:
            batch_size = 10

        for df in RestrictedLoader(
            session=session,
            sequence_model=sequence,
            number_shots=number_shots_to_load,
            batch_size=batch_size,
            metadata_schema=restricted_metadata_schema,
            parameter_schema=restricted_parameter_schema,
            data_schema=restricted_data_schema,
        )():
            if with_columns is not None:
                df = df.select(with_columns)
            if predicate is not None:
                df = df.filter(predicate)
            yield df

    return register_io_source(load, pl_schema)


def get_shot_metadata_pl_schema() -> dict[str, polars.DataType]:
    return {
        "sequence": polars.Categorical(ordering="lexical"),
        "shot_index": polars.UInt64(),
        "shot_start_time": polars.Datetime(time_unit="ms", time_zone="UTC"),
        "shot_end_time": polars.Datetime(time_unit="ms", time_zone="UTC"),
    }


def get_parameter_pl_schema(
    parameter_schema: Mapping[str, ParameterType],
) -> dict[str, polars.DataType]:
    return {
        parameter: parameter_type.to_polars_dtype()
        for parameter, parameter_type in parameter_schema.items()
    }


def structure_shot_sql_data(data: SQLStructuredShotData | SQLShotArray) -> Data:
    match data:
        case SQLStructuredShotData(content=content):
            return content
        case SQLShotArray(bytes_=bytes_, shape=shape, dtype=dtype):
            return np.frombuffer(bytes_, dtype=dtype).reshape(shape)
        case _:
            assert_never(data)
