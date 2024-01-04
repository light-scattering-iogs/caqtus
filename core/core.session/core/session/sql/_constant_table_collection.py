import datetime
import uuid
from typing import TYPE_CHECKING

import attrs
import sqlalchemy

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from ._constant_tables import (
    SQLConstantTable,
    SQLConstantDeclaration,
    SQLCurrentConstantTables,
)
from ..constant_table_collection import ConstantTableCollection, ConstantTable
from ..sequence.iteration_configuration import VariableDeclaration

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.frozen
class SQLConstantTableCollection(
    ConstantTableCollection,
):
    parent_session: "SQLExperimentSession"

    def add_table(
        self,
        table_name: str,
        table: ConstantTable,
    ) -> uuid.UUID:
        creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        uuid_ = self._create_uuid(table_name, creation_date)
        declarations = [
            SQLConstantDeclaration(
                variable=declaration.variable,
                expression=declaration.value,
            )
            for declaration in table
        ]
        new = SQLConstantTable(
            uuid=uuid_,
            name=table_name,
            creation_date=creation_date,
            constant_declarations=declarations,
        )
        self._get_sql_session().add(new)
        return uuid_

    def get_table_name(self, uuid_: uuid.UUID) -> str:
        return self._get_table(uuid_).name

    def get_table(self, uuid_: uuid.UUID) -> ConstantTable:
        table = self._get_table(uuid_)
        declarations = [
            VariableDeclaration(
                variable=DottedVariableName(declaration.variable),
                value=Expression(declaration.expression),
            )
            for declaration in table.constant_declarations
        ]
        return declarations

    def set_in_use(self, uuid_: uuid.UUID) -> None:
        new = SQLCurrentConstantTables(
            in_use=uuid_,
            table_name=self.get_table_name(uuid_),
        )
        self._get_sql_session().add(new)

    def remove_from_use(self, uuid_: uuid.UUID):
        action = sqlalchemy.delete(SQLCurrentConstantTables).where(
            SQLCurrentConstantTables.in_use == uuid_
        )
        self._get_sql_session().execute(action)

    def get_in_use_uuids(self) -> set[uuid.UUID]:
        query = sqlalchemy.select(SQLCurrentConstantTables.in_use)
        return {id_ for id_, in self._get_sql_session().execute(query)}

    def _get_table(self, uuid_: uuid.UUID) -> SQLConstantTable:
        query = sqlalchemy.select(SQLConstantTable).where(
            SQLConstantTable.uuid == uuid_
        )
        return self._get_sql_session().execute(query).scalar_one()

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
