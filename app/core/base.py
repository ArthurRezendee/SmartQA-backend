from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.inspection import inspect
from app.core.timestamps import TimestampMixin


class Base(DeclarativeBase, TimestampMixin):
    """
    Base de todos os models do SmartQA
    """

    def to_dict(self):
        return {
            column.key: getattr(self, column.key)
            for column in inspect(self).mapper.column_attrs
        }
