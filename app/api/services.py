from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schema import Service

router = APIRouter(prefix="/services", tags=["services"])

@router.get("/")
def get_all_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description
        } for s in services
    ]
