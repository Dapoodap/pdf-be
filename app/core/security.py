from datetime import datetime, timedelta
from typing import Optional
import time
from collections import defaultdict
from fastapi import Request, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.schema import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    return api_key

# --- Rate Limiter ---
# Menyimpan timestamps requests per IP. Menggunakan defaultdict agar tidak ada KeyError.
# Memory leak fix: kita lakukan cleanup periodik menggunakan threshold MAX_TRACKED_IPS.
# Jika jumlah IP yang dilacak melebihi batas, IP yang sudah lama tidak aktif akan dihapus.
GUEST_RATE_LIMITS: dict[str, list[float]] = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 5
MAX_TRACKED_IPS = 10_000  # Batas maksimal IP yang dilacak sebelum di-cleanup
_last_cleanup_time = 0.0
CLEANUP_INTERVAL_SECONDS = 300  # Cleanup global setiap 5 menit

def _cleanup_stale_ips(now: float):
    """Hapus entri IP yang sudah tidak ada aktivitas dalam 2 menit terakhir."""
    global _last_cleanup_time
    if now - _last_cleanup_time < CLEANUP_INTERVAL_SECONDS:
        return
    _last_cleanup_time = now
    stale_ips = [ip for ip, timestamps in GUEST_RATE_LIMITS.items() if not timestamps or now - max(timestamps) > 120]
    for ip in stale_ips:
        del GUEST_RATE_LIMITS[ip]


async def get_optional_current_user(
    request: Request,
    api_key: str = Depends(verify_api_key),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    if not token:
        # Ambil IP dari header proxy, fallback ke host langsung
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        now = time.time()

        # Jalankan cleanup berkala untuk mencegah memory leak
        if len(GUEST_RATE_LIMITS) > MAX_TRACKED_IPS:
            _cleanup_stale_ips(now)
        else:
            _cleanup_stale_ips(now)

        # Filter hanya timestamps dalam 60 detik terakhir
        GUEST_RATE_LIMITS[client_ip] = [ts for ts in GUEST_RATE_LIMITS[client_ip] if now - ts < 60]

        if len(GUEST_RATE_LIMITS[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for guest access ({MAX_REQUESTS_PER_MINUTE} requests/minute). Please login for unlimited access.",
                headers={"Retry-After": "60"}
            )

        GUEST_RATE_LIMITS[client_ip].append(now)
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user(current_user: User | None = Depends(get_optional_current_user)):
    if not current_user or current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user
