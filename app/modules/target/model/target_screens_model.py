from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime, func
from app.core.base import Base
import datetime

class TargetScreen(Base):
    __tablename__ = "target_screens"

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    id = Column(Integer, primary_key=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    screen_id = Column(
        Integer,
        ForeignKey("screens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("target_id", "screen_id", name="uq_target_screens"),
    )
