import sqlalchemy.orm
from sqlalchemy import JSON, LargeBinary

from caqtus.utils.serialization import JsonDict, JSON as Json


class Base(sqlalchemy.orm.DeclarativeBase):
    type_annotation_map = {JsonDict: JSON, bytes: LargeBinary, Json: JSON}
