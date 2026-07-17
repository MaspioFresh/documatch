from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String, index=True)
    action = Column(String, index=True)
    target_id = Column(String, nullable=True, index=True)
    details = Column(String, nullable=True)
