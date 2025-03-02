import sqlalchemy.orm
import sqlalchemy.types

from caqtus.utils.serialization import JsonDict


class Base(sqlalchemy.orm.DeclarativeBase):
    type_annotation_map = {JsonDict: sqlalchemy.types.JSON}
