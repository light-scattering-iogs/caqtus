from __future__ import annotations

import sqlalchemy
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ._table_base import Base


# This table stores parameters that can be shared across sequences.
# Each set of parameters is identified by a unique name and stores a JSON object
# representing a ParameterNamespace.
# At the moment, there is only one row in this table, which stores the so-called
# "global" parameters.
class SQLParameters(Base):
    __tablename__ = "parameters"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    content = mapped_column(sqlalchemy.types.JSON)
