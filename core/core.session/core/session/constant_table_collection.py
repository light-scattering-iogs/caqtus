import abc
import datetime
import uuid
from collections.abc import MutableMapping
from typing import TypeAlias

from .sequence.iteration_configuration import VariableDeclaration

ConstantTable: TypeAlias = list[VariableDeclaration]


class ConstantTableCollection(MutableMapping[str, ConstantTable], abc.ABC):
    """A collection of constant tables.

    Instances of this class give access to the constant tables are used to define
    constant parameters in a sequence.
    Each table has a unique uuid identifier, and a name (which is not unique).
    Typically, a table with a given name exists with different uuids corresponding to
    each update of the table.

    In addition, a subset of tables are defined as the default tables.
    These tables are used when constant tables are required, but no table is specified.
    In this set of default tables, each table has a unique name.
    The ConstantTableCollection class provides a mapping interface to access the default
    tables.
    It is possible to add or remove tables from the default tables using the mapping
    interface.
    """
    def __len__(self):
        return len(self.get_default_uuids())

    def __iter__(self):
        in_use_uuids = self.get_default_uuids()
        table_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        return iter(table_uuids)

    def __getitem__(self, key):
        in_use_uuids = self.get_default_uuids()
        table_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        table_uuid = table_uuids[key]
        return self.get_table(table_uuid)

    def __setitem__(self, key, value):
        id_ = self.add_table(key, value)
        in_use_uuids = self.get_default_uuids()
        tables_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        if key in tables_uuids:
            self.remove_from_defaults(tables_uuids[key])
        self.add_to_defaults(id_)

    def __delitem__(self, key):
        in_use_uuids = self.get_default_uuids()
        tables_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        table_uuid = tables_uuids[key]
        self.remove_from_defaults(table_uuid)

    @abc.abstractmethod
    def get_table_name(self, id_: uuid.UUID) -> str:
        """Get the name of the constant table with the given id."""

        ...

    @abc.abstractmethod
    def get_table(self, id_: uuid.UUID) -> ConstantTable:
        """Get the constant table with the given UUID."""

        ...

    def get_default_tables(self) -> dict[str, uuid.UUID]:
        """Returns the tables that are used by default."""

        return {self.get_table_name(uuid_): uuid_ for uuid_ in self.get_default_uuids()}

    @abc.abstractmethod
    def add_table(
        self,
        table_name: str,
        table: ConstantTable,
    ) -> uuid.UUID:
        """Add a new constant table to the session.

        Args:
            table_name: the name of the constant table.
            table: the constant table to add to the session.

        Returns:
            The UUID of the constant table.
        """

        ...

    @abc.abstractmethod
    def add_to_defaults(self, id_: uuid.UUID) -> None:
        """Add the table with this uuid to the defaults one.

        If another constant table with the same name is already in use, it will be
        replaced by this one.
        """

        ...

    @abc.abstractmethod
    def remove_from_defaults(self, id_: uuid.UUID) -> None:
        """Remove the constant table from the in use tables."""

        ...

    @abc.abstractmethod
    def get_default_uuids(self) -> set[uuid.UUID]:
        """Get the constant tables that must be used by default."""

        ...

    @staticmethod
    def _create_uuid(table_name: str, date: datetime.datetime) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}/{date}")
