from collections.abc import Iterator, Mapping

import attrs
import polars
from polars.io.plugins import register_io_source
from sqlalchemy import select
from sqlalchemy.orm import Session
from tqdm.auto import tqdm

from caqtus.types.parameter import Parameter, ParameterType, converter
from caqtus.types.units import Quantity
from ._sequence_table import SQLSequence
from ._shot_tables import SQLShot, SQLShotParameter

structure_parameter = converter.get_structure_hook(bool | int | float | Quantity)


@attrs.frozen
class RestrictedLoader:
    session: Session
    sequence_model: SQLSequence
    number_shots: int
    batch_size: int
    metadata_schema: dict[str, polars.DataType]
    parameter_schema: Mapping[str, ParameterType]

    def __call__(self) -> Iterator[polars.DataFrame]:
        sequence_name = self.sequence_model.path.path
        shots_query = (
            select(SQLShot, SQLShotParameter)
            .where(
                SQLShot.sequence == self.sequence_model,
                SQLShot.index < self.number_shots,
            )
            .join(SQLShotParameter)
            .order_by(SQLShot.index)
            .execution_options(yield_per=self.batch_size)
        )
        pl_parameter_schema = get_parameter_pl_schema(self.parameter_schema)
        for shot, parameters in tqdm(
            self.session.execute(shots_query).tuples(), total=self.number_shots
        ):
            shot_metadata = {}
            if "sequence" in self.metadata_schema:
                shot_metadata["sequence"] = (sequence_name,)
            if "shot_index" in self.metadata_schema:
                shot_metadata["shot_index"] = (shot.index,)
            if "shot_start_time" in self.metadata_schema:
                shot_metadata["shot_start_time"] = (shot.get_start_time(),)
            if "shot_end_time" in self.metadata_schema:
                shot_metadata["shot_end_time"] = (shot.get_end_time(),)
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

            df = polars.concat([metadata_df, parameter_df], how="horizontal")

            yield df


def lazy_load(
    session: Session,
    sequence: SQLSequence,
    parameter_schema: Mapping[str, ParameterType],
) -> polars.LazyFrame:
    pl_shot_metadata_schema = get_shot_metadata_pl_schema()
    pl_parameter_schema = get_parameter_pl_schema(parameter_schema)
    pl_schema = pl_shot_metadata_schema | pl_parameter_schema

    def load(
        with_columns: list[str] | None,
        predicate: polars.Expr | None,
        n_rows: int | None,
        batch_size: int | None,
    ) -> Iterator[polars.DataFrame]:
        if with_columns is None:
            restricted_metadata_schema = pl_shot_metadata_schema
            restricted_parameter_schema = parameter_schema
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
        "shot_start_time": polars.Datetime(),
        "shot_end_time": polars.Datetime(),
    }


def get_parameter_pl_schema(
    parameter_schema: Mapping[str, ParameterType],
) -> dict[str, polars.DataType]:
    return {
        parameter: parameter_type.to_polars_dtype()
        for parameter, parameter_type in parameter_schema.items()
    }
