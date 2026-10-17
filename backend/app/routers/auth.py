from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
        raise HTTPException(400, "Логин или email уже заняты")
    u = User(username=data.username.strip(), email=data.email.strip().lower(),
             password_hash=hash_password(data.password))
    db.add(u)
    db.commit()
    return TokenOut(access_token=create_access_token(u.username))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == data.username).first()
    if not u or not verify_password(data.password, u.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return TokenOut(access_token=create_access_token(u.username))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin}
