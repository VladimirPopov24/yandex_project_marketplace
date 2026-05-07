from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi import Request

SECRET_KEY = "modex-jwt-secret-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def get_password_hash(password: str) -> str:
    return generate_password_hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    return user if user and not user.is_blocked else None
