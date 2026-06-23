from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.schema import FileHistory, User, Subscription
from app.services import storage

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/{history_id}/download-url")
def get_download_url(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = db.query(FileHistory).filter(FileHistory.id == history_id).first()

    if not history:
        raise HTTPException(status_code=404, detail="File history not found")

    # SECURITY: Pastikan file ini milik user yang sedang login
    if history.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: This file does not belong to you")

    try:
        url = storage.generate_presigned_url(history.file_path)
        return {"url": url, "expires_in": "60 minutes", "file_name": history.file_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def get_my_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek apakah user premium berdasarkan subscription aktif
    now = datetime.utcnow()
    active_sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > now
    ).first()

    is_premium = active_sub is not None

    query = db.query(FileHistory).options(
        joinedload(FileHistory.service)
    ).filter(FileHistory.user_id == current_user.id)

    # User non-premium hanya bisa lihat history 24 jam terakhir
    if not is_premium:
        limit_date = datetime.utcnow() - timedelta(days=1)
        query = query.filter(FileHistory.created_at >= limit_date)

    histories = query.order_by(FileHistory.created_at.desc()).all()

    return [
        {
            "id": h.id,
            "service": {
                "id": h.service.id,
                "name": h.service.name,
                "description": h.service.description,
            } if h.service else None,
            "file_name": h.file_name,
            "file_type": h.file_type,
            "created_at": h.created_at,
        }
        for h in histories
    ]
