from sqlalchemy.orm import DeclarativeBase
from app.core.timestamps import TimestampMixin


class Base(DeclarativeBase, TimestampMixin):
    """
    Base de todos os models do SmartQA
    """
    pass
