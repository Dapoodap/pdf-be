from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schema import Transaction, User, Pricing, Subscription
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/transaction", tags=["transaction"])

class TransactionCreate(BaseModel):
    amount: float
    status: str

class SubscribeRequest(BaseModel):
    pricing_id: int
    order_id: str | None = None
    transaction_id: str | None = None
    payment_type: str | None = None
    transaction_status: str | None = None
    gross_amount: float | None = None

@router.post("/")
def create_transaction(
    data: TransactionCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        new_transaction = Transaction(
            user_id=current_user.id,
            amount=data.amount,
            status=data.status
        )
        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
        return {
            "message": "Transaction created successfully", 
            "transaction_id": new_transaction.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_transactions(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc()).all()
        return [
            {
                "id": t.id,
                "amount": t.amount,
                "status": t.status,
                "created_at": t.created_at
            } for t in transactions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe")
def subscribe(
    data: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        pricing = db.query(Pricing).filter(Pricing.id == data.pricing_id).first()
        if not pricing:
            raise HTTPException(status_code=404, detail="Pricing plan not found")
        if not pricing.duration_days:
            raise HTTPException(status_code=400, detail="Pricing plan missing duration_days")

        current_time = datetime.utcnow()
        
        latest_sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).order_by(Subscription.end_date.desc()).first()
        if latest_sub:
            latest_end = latest_sub.end_date
            if latest_end.tzinfo is None:
                latest_end = latest_end.replace(tzinfo=datetime.timezone.utc)
            
            current_time_aware = current_time.replace(tzinfo=datetime.timezone.utc)
            if latest_end > current_time_aware:
                start_time = latest_end
            else:
                start_time = current_time
        else:
            start_time = current_time
            
        end_time = start_time + timedelta(days=pricing.duration_days)

        new_transaction = Transaction(
            user_id=current_user.id,
            amount=data.gross_amount if data.gross_amount is not None else pricing.price,
            status=data.transaction_status if data.transaction_status else "success",
            order_id=data.order_id if data.order_id else f"ORDER-{uuid.uuid4().hex[:8].upper()}",
            midtrans_transaction_id=data.transaction_id,
            payment_type=data.payment_type
        )
        db.add(new_transaction)

        new_subscription = Subscription(
            user_id=current_user.id,
            pricing_id=pricing.id,
            start_date=start_time,
            end_date=end_time
        )
        db.add(new_subscription)

        current_user.membership_status = "premium"
        
        db.commit()
        db.refresh(new_transaction)
        db.refresh(new_subscription)
        
        return {
            "message": "Subscription successful",
            "transaction_id": new_transaction.id,
            "subscription_id": new_subscription.id,
            "start_date": new_subscription.start_date,
            "end_date": new_subscription.end_date
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
