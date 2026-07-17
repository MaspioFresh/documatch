from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username: str
    action: str
    target_id: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True
