import datetime as dt
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import ApiKey, User

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

ALGO = "HS256"


def hash_password(p: str) -> str:
    return pwd_ctx.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)


def create_access_token(sub: str) -> str:
    exp = dt.datetime.utcnow() + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": sub, "exp": exp}, settings.SECRET_KEY, algorithm=ALGO)


def create_paid_token(code: str) -> str:
    exp = dt.datetime.utcnow() + dt.timedelta(minutes=settings.PAID_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"paid": code, "exp": exp}, settings.SECRET_KEY, algorithm=ALGO)


def check_paid_token(token: str, code: str) -> bool:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        return data.get("paid") == code
    except JWTError:
        return False


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    # 1) JWT
    if creds and creds.credentials:
        try:
            data = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[ALGO])
            sub = data.get("sub")
            if sub:
                u = db.query(User).filter(User.username == sub).first()
                if u:
                    return u
        except JWTError:
            pass
    return None


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    return user


def auth_user_or_apikey(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Принимает JWT либо API-ключ вида `lm_<secret>` в Authorization: Bearer."""
    if not creds or not creds.credentials:
        return None
    token = creds.credentials
    # API-ключ
    if token.startswith("lm_"):
        prefix = token[:10]
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = db.query(ApiKey).filter(ApiKey.key_prefix == prefix, ApiKey.key_hash == digest).first()
        if row:
            row.last_used_at = dt.datetime.utcnow()
            db.commit()
            return db.query(User).filter(User.id == row.user_id).first()
        return None
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        sub = data.get("sub")
        if sub:
            return db.query(User).filter(User.username == sub).first()
    except JWTError:
        return None
    return None


def require_user(user: User | None = Depends(auth_user_or_apikey)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация (JWT или API-ключ)")
    return user


def new_api_key() -> tuple[str, str, str]:
    secret = "lm_" + secrets.token_urlsafe(32)
    prefix = secret[:10]
    digest = hashlib.sha256(secret.encode()).hexdigest()
    return secret, prefix, digest
