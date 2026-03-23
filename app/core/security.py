from app.core.config import settings
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_email_confirmation_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "purpose": "email_confirmation",
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_email_confirmation_token(token: str) -> int:
    """Retorna o user_id se válido, levanta jwt.InvalidTokenError caso contrário."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("purpose") != "email_confirmation":
        raise jwt.InvalidTokenError("Token inválido")
    return int(payload["sub"])
