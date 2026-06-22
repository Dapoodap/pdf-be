from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schema import Pricing

router = APIRouter(prefix="/pricing", tags=["pricing"])

@router.get("/")
def get_pricings(db: Session = Depends(get_db)):
    try:
        pricings = db.query(Pricing).all()
        return [
            {
                "id": p.id,
                "price": p.price,
                "description": p.description,
                "plan_type": p.plan_type,
                "duration_days": p.duration_days
            } for p in pricings
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
