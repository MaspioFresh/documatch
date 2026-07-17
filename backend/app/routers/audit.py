from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse
from app.core.security import get_current_admin

router = APIRouter(
    prefix="/audit",
    tags=["audit"]
)

@router.get("/", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: str = Depends(get_current_admin)
):
    # Solo l'amministratore supremo può vedere i log.
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Non autorizzato a visualizzare i log")
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs
