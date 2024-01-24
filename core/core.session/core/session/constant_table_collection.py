import abc
import datetime
import uuid
from collections.abc import MutableMapping
from typing import TypeAlias

from .sequence.iteration_configuration import VariableDeclaration

ConstantTable: TypeAlias = list[VariableDeclaration]


class ConstantTableCollection(MutableMapping[str, ConstantTable], abc.ABC):
    def __len__(self):
        return len(self.get_in_use_uuids())

    def __iter__(self):
        in_use_uuids = self.get_in_use_uuids()
        table_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        return iter(table_uuids)

    def __getitem__(self, key):
        in_use_uuids = self.get_in_use_uuids()
        table_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        table_uuid = table_uuids[key]
        return self.get_table(table_uuid)

    def __setitem__(self, key, value):
        id_ = self.add_table(key, value)
        in_use_uuids = self.get_in_use_uuids()
        tables_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        if key in tables_uuids:
            self.remove_from_use(tables_uuids[key])
        self.set_in_use(id_)

    def __delitem__(self, key):
        in_use_uuids = self.get_in_use_uuids()
        tables_uuids = {self.get_table_name(id_): id_ for id_ in in_use_uuids}
        table_uuid = tables_uuids[key]
        self.remove_from_use(table_uuid)

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

        return {self.get_table_name(uuid_): uuid_ for uuid_ in self.get_in_use_uuids()}

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
    def set_in_use(self, id_: uuid.UUID) -> None:
        """Set the constant table to be in use.

        If another constant table with the same name is already in use, it will be
        replaced by this one.
        """

        ...

    @abc.abstractmethod
    def remove_from_use(self, id_: uuid.UUID) -> None:
        """Remove the constant table from the in use tables."""

        ...

    @abc.abstractmethod
    def get_in_use_uuids(self) -> set[uuid.UUID]:
        """Get the constant tables that are in use."""

        ...

    @staticmethod
    def _create_uuid(table_name: str, date: datetime.datetime) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}/{date}")
