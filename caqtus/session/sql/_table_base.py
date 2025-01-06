import sqlalchemy.orm
from sqlalchemy import JSON

from caqtus.utils.serialization import JsonDict


class Base(sqlalchemy.orm.DeclarativeBase):
    type_annotation_map = {JsonDict: JSON}
