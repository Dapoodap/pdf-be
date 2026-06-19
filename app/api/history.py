from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from app.core.security import get_optional_current_user
from app.core.database import get_db
from app.models.schema import FileHistory, User
from app.services import storage

router = APIRouter(prefix="/history", tags=["history"], dependencies=[Depends(get_optional_current_user)])

@router.get("/{history_id}/download-url")
def get_download_url(history_id: int, db: Session = Depends(get_db)):
    history = db.query(FileHistory).filter(FileHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="File history not found")
        
    try:
        url = storage.generate_presigned_url(history.file_path)
        return {"url": url, "expires_in": "60 minutes", "file_name": history.file_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}")
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    query = db.query(FileHistory).options(joinedload(FileHistory.service)).filter(FileHistory.user_id == user_id)
    
    if not user.is_premium:
        limit_date = datetime.utcnow() - timedelta(days=1)
        query = query.filter(FileHistory.created_at >= limit_date)
        
    histories = query.order_by(FileHistory.created_at.desc()).all()
    
    return [
        {
            "id": h.id,
            "service": {
                "id": h.service.id,
                "name": h.service.name,
                "description": h.service.description
            } if h.service else None,
            "file_name": h.file_name,
            "file_type": h.file_type,
            "created_at": h.created_at
        } for h in histories
    ]
