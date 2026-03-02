from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import get_settings

# Use pbkdf2 to avoid platform-specific bcrypt issues in containers
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_signing_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    last_error: Exception | None = None
    for key in settings.jwt_verification_keys:
        try:
            return jwt.decode(token, key, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise JWTError("Token verification failed")
