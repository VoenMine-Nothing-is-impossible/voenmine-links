from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import new_api_key, require_user
from ..database import get_db
from ..models import ApiKey, User
from ..schemas import ApiKeyCreate, ApiKeyOut

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
def list_keys(db: Session = Depends(get_db), user: User = Depends(require_user)):
    return db.query(ApiKey).filter(ApiKey.user_id == user.id).all()


@router.post("")
def create_key(data: ApiKeyCreate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    secret, prefix, digest = new_api_key()
    row = ApiKey(user_id=user.id, name=data.name[:128], key_prefix=prefix, key_hash=digest)
    db.add(row)
    db.commit()
    return {"api_key": secret, "prefix": prefix,
            "hint": "Передавайте как Authorization: Bearer <ключ>. Сохраните — больше не покажем."}


@router.delete("/{key_id}")
def revoke_key(key_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    row = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Ключ не найден")
    db.delete(row)
    db.commit()
    return {"ok": True}
