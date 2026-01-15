from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.base import Base

class ProcessNotification(Base):
    __tablename__ = "process_notifications"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=False)

    process_key = Column(String(100), nullable=False)

    title = Column(String(255), nullable=False)

    status = Column(String(50), nullable=False, default="running")
    progress = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
