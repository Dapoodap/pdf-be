from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.models.schema import User, FileHistory

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
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_processed = db.query(func.count(FileHistory.id)).filter(FileHistory.user_id == current_user.id).scalar()
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_premium": current_user.is_premium,
        "total_files_processed": total_processed or 0
    }
