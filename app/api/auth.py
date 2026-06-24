from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import random
import string

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.models.schema import User, FileHistory, Subscription

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter((User.username == request.username) | (User.email == request.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
        
    hashed_password = get_password_hash(request.password)
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": f"Registration successful for {new_user.username}."}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


class GoogleAuthRequest(BaseModel):
    token: str

@router.post("/google")
def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from app.core.config import settings
    import secrets

    try:
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            request.token, 
            google_requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get("email")
        name = idinfo.get("name") or idinfo.get("given_name") or email.split('@')[0]
        
        if not email:
            raise HTTPException(status_code=400, detail="Google token does not contain email")
            
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Check if username is taken, append random string if needed
            existing_username = db.query(User).filter(User.username == name).first()
            if existing_username:
                name = f"{name}_{secrets.token_hex(2)}"
                
            # Create a new user with a random unguessable password
            random_password = secrets.token_urlsafe(16)
            hashed_password = get_password_hash(random_password)
            
            user = User(
                username=name,
                email=email,
                hashed_password=hashed_password
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # Generate our local JWT access token
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
        
    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

import datetime

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_processed = db.query(func.count(FileHistory.id)).filter(FileHistory.user_id == current_user.id).scalar()
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    latest_sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).order_by(Subscription.end_date.desc()).first()
    
    premium_status = "basic"
    sub_start = None
    sub_end = None
    
    if latest_sub:
        end_date = latest_sub.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=datetime.timezone.utc)
            
        sub_start = latest_sub.start_date
        sub_end = latest_sub.end_date
            
        if end_date > now:
            premium_status = "premium"
        else:
            premium_status = "expired"
            
    if current_user.membership_status != premium_status:
        current_user.membership_status = premium_status
        db.commit()
            
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "membership_status": premium_status,
        "subscription_start_date": sub_start,
        "subscription_end_date": sub_end,
        "total_files_processed": total_processed or 0
    }
