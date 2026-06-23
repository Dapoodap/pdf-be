import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schema import Transaction, User, Pricing, Subscription
from app.core.config import settings
from datetime import datetime, timedelta
import uuid
import httpx

logger = logging.getLogger(__name__)
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


async def _verify_midtrans_payment(order_id: str) -> dict:
    """
    Verifies payment status directly with Midtrans server API.
    Returns the transaction data if valid and settled.
    Raises HTTPException if payment cannot be verified.
    """
    if not settings.MIDTRANS_SERVER_KEY:
        logger.warning("MIDTRANS_SERVER_KEY not configured — skipping payment verification")
        return {}

    import base64
    encoded_key = base64.b64encode(f"{settings.MIDTRANS_SERVER_KEY}:".encode()).decode()
    url = f"https://api.sandbox.midtrans.com/v2/{order_id}/status"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"Authorization": f"Basic {encoded_key}"},
                timeout=10.0
            )
        except Exception as e:
            logger.error(f"Failed to reach Midtrans API: {e}")
            raise HTTPException(status_code=502, detail="Could not verify payment with payment provider. Please try again.")

    if response.status_code == 404:
        raise HTTPException(status_code=400, detail="Order not found in payment system. Please complete payment first.")

    data = response.json()
    transaction_status = data.get("transaction_status", "")
    fraud_status = data.get("fraud_status", "accept")

    # Only accept settled or captured payments
    valid_statuses = {"settlement", "capture"}
    if transaction_status not in valid_statuses or fraud_status == "deny":
        raise HTTPException(
            status_code=400,
            detail=f"Payment has not been confirmed. Current status: '{transaction_status}'. "
                   f"Please complete your payment before activating premium."
        )

    return data


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
        logger.error(f"create_transaction error for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create transaction.")


@router.get("/")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user.id
        ).order_by(Transaction.created_at.desc()).all()
        return [
            {
                "id": t.id,
                "amount": t.amount,
                "status": t.status,
                "created_at": t.created_at
            } for t in transactions
        ]
    except Exception as e:
        logger.error(f"get_transactions error for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions.")


@router.post("/subscribe")
async def subscribe(
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

        # ── SECURITY: Verify payment with Midtrans before activating premium ──
        if data.order_id:
            await _verify_midtrans_payment(data.order_id)
        else:
            # No order_id provided — reject unless server key is not configured (dev mode)
            if settings.MIDTRANS_SERVER_KEY:
                raise HTTPException(
                    status_code=400,
                    detail="order_id is required to verify payment."
                )

        current_time = datetime.utcnow()

        latest_sub = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).order_by(Subscription.end_date.desc()).first()

        if latest_sub and latest_sub.end_date:
            latest_end = latest_sub.end_date
            if latest_end.tzinfo is None:
                from datetime import timezone
                latest_end = latest_end.replace(tzinfo=timezone.utc)
            current_time_aware = current_time.replace(tzinfo=timezone.utc)
            start_time = latest_end if latest_end > current_time_aware else current_time
        else:
            start_time = current_time

        end_time = start_time + timedelta(days=pricing.duration_days)

        new_transaction = Transaction(
            user_id=current_user.id,
            amount=data.gross_amount if data.gross_amount is not None else pricing.price,
            status="settlement",  # hardcoded — verified above
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
        logger.error(f"subscribe error for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to activate subscription.")
