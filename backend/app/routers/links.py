import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user_optional, hash_password, require_user
from ..cache import invalidate_link
from ..config import settings
from ..database import get_db
from ..limits import limiter
from ..metrics import CREATED
from ..models import Link, Tag, User
from ..schemas import LinkCreate, LinkOut, LinkUpdate, Trackers
from ..utils import gen_code, normalize_url, validate_slug

router = APIRouter(prefix="/api/links", tags=["links"])


def link_to_out(l: Link) -> LinkOut:
    return LinkOut(
        id=l.id, code=l.code,
        short_url=settings.PUBLIC_BASE_URL.rstrip("/") + "/" + l.code,
        target_url=l.target_url, fallback_url=l.fallback_url,
        expires_at=l.expires_at, max_clicks=l.max_clicks, clicks_count=l.clicks_count,
        is_active=l.is_active, has_password=bool(l.password_hash),
        is_paid=l.price_amount is not None and l.price_amount > 0,
        price_amount=l.price_amount, show_preview=l.show_preview,
        og_title=l.og_title, og_description=l.og_description, og_image=l.og_image,
        tags=[t.name for t in (l.tags_rel or [])],
        webhook_url=l.webhook_url, created_at=l.created_at,
    )


def _sync_tags(db: Session, user: User | None, link: Link, names: list[str]):
    link.tags_rel = []
    if user is None:
        return
    for raw in names[:20]:
        name = (raw or "").strip().lower()[:64]
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.user_id == user.id, Tag.name == name).first()
        if not tag:
            tag = Tag(user_id=user.id, name=name)
            db.add(tag)
            db.flush()
        link.tags_rel.append(tag)


@router.post("", response_model=LinkOut)
@limiter.limit(f"{settings.RATE_CREATE_PER_MIN}/minute")
def create_link(request: Request, data: LinkCreate, db: Session = Depends(get_db),
                user: User | None = Depends(get_current_user_optional)):
    try:
        target = normalize_url(data.target_url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    fallback = None
    if data.fallback_url:
        try:
            fallback = normalize_url(data.fallback_url)
        except ValueError as e:
            raise HTTPException(400, f"Резервный адрес: {e}")
    if data.webhook_url:
        try:
            normalize_url(data.webhook_url)
        except ValueError:
            raise HTTPException(400, "Некорректный webhook URL (нужен http(s))")

    # Дедупликация: та же целевая ссылка + те же параметры у того же
    # пользователя → вернуть ранее созданный код, а не плодить дубликаты.
    # Сравниваются: target, expires_at, max_clicks, наличие пароля,
    # price_amount, show_preview, webhook_url, fallback_url, OG, трекеры, теги.
    def _norm_exp(v):
        return v.replace(tzinfo=None) if v else None

    want_exp = _norm_exp(data.expires_at)
    want_has_pw = bool(data.password)
    want_trackers = json.dumps((data.trackers or Trackers()).model_dump() if hasattr(data.trackers, "model_dump") else {}, sort_keys=True)
    want_tags = sorted([(t or "").strip().lower() for t in (data.tags or []) if (t or "").strip()]) if data.tags else []
    if user and not data.slug:
        candidates = db.query(Link).filter(
            Link.owner_id == user.id,
            Link.target_url == target,
            Link.is_active.is_(True),
        ).order_by(Link.created_at.desc()).limit(20).all()
        for dup in candidates:
            dup_exp = dup.expires_at.replace(tzinfo=None) if dup.expires_at else None
            if dup_exp != want_exp:
                continue
            if (dup.max_clicks or None) != (data.max_clicks or None):
                continue
            if bool(dup.password_hash) != want_has_pw:
                continue
            if (dup.price_amount or None) != (data.price_amount or None):
                continue
            if bool(dup.show_preview) != bool(data.show_preview):
                continue
            if (dup.webhook_url or None) != (data.webhook_url or None):
                continue
            if (dup.fallback_url or None) != (fallback or None):
                continue
            if (dup.og_title or None) != (data.og_title or None):
                continue
            if (dup.og_description or None) != (data.og_description or None):
                continue
            if (dup.og_image or None) != (data.og_image or None):
                continue
            try:
                dup_tr = json.dumps(json.loads(dup.trackers or "{}"), sort_keys=True)
            except Exception:
                dup_tr = "{}"
            if dup_tr != want_trackers:
                continue
            dup_tags = sorted([t.name for t in (dup.tags_rel or [])])
            if dup_tags != want_tags:
                continue
            return link_to_out(dup)

    code = None
    is_custom = False
    if data.slug:
        try:
            code = validate_slug(data.slug)
        except ValueError as e:
            raise HTTPException(400, str(e))
        is_custom = True
        if db.query(Link).filter(Link.code == code).first():
            raise HTTPException(409, "Такой алиас уже занят")
    else:
        for _ in range(8):
            c = gen_code(settings.DEFAULT_SLUG_LEN)
            if not db.query(Link).filter(Link.code == c).first():
                code = c
                break
        if not code:
            raise HTTPException(500, "Не удалось сгенерировать код")

    link = Link(
        owner_id=user.id if user else None, code=code, target_url=target,
        fallback_url=fallback, is_custom=is_custom,
        password_hash=hash_password(data.password) if data.password else None,
        expires_at=data.expires_at.replace(tzinfo=None) if data.expires_at else None,
        max_clicks=data.max_clicks, show_preview=data.show_preview,
        og_title=data.og_title, og_description=data.og_description, og_image=data.og_image,
        trackers=json.dumps(data.trackers.model_dump()),
        webhook_url=data.webhook_url, price_amount=data.price_amount,
    )
    db.add(link)
    db.flush()
    _sync_tags(db, user, link, data.tags)
    db.commit()
    db.refresh(link)
    CREATED.inc()
    return link_to_out(link)


@router.get("", response_model=list[LinkOut])
def my_links(status: str = Query("all"), tag: str | None = None,
             q: str | None = None, db: Session = Depends(get_db),
             user: User = Depends(require_user)):
    query = db.query(Link).filter(Link.owner_id == user.id)
    now = dt.datetime.utcnow()
    if status == "active":
        query = query.filter(Link.is_active.is_(True))
    elif status == "expired":
        query = query.filter(or_(Link.is_active.is_(False),
                                         Link.expires_at.isnot(None) & (Link.expires_at <= now)))
    elif status == "limited":
        query = query.filter(Link.max_clicks.isnot(None), Link.clicks_count >= Link.max_clicks)
    if q:
        query = query.filter(or_(Link.code.ilike(f"%{q}%"), Link.target_url.ilike(f"%{q}%")))
    links = query.order_by(Link.created_at.desc()).limit(500).all()
    if tag:
        links = [l for l in links if tag.lower() in [t.name for t in l.tags_rel]]
    return [link_to_out(l) for l in links]


@router.get("/{code}", response_model=LinkOut)
def get_link(code: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    l = db.query(Link).filter(Link.code == code).first()
    if not l or (l.owner_id != user.id and not user.is_admin):
        raise HTTPException(404, "Ссылка не найдена")
    return link_to_out(l)


@router.patch("/{code}", response_model=LinkOut)
async def update_link(code: str, data: LinkUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_user)):
    l = db.query(Link).filter(Link.code == code).first()
    if not l or (l.owner_id != user.id and not user.is_admin):
        raise HTTPException(404, "Ссылка не найдена")
    if data.target_url:
        try:
            l.target_url = normalize_url(data.target_url)
        except ValueError as e:
            raise HTTPException(400, str(e))
    if data.fallback_url is not None:
        l.fallback_url = normalize_url(data.fallback_url) if data.fallback_url else None
    if data.password is not None:
        l.password_hash = hash_password(data.password) if data.password else None
    if data.expires_at is not None:
        l.expires_at = data.expires_at.replace(tzinfo=None) if data.expires_at else None
    for f in ("max_clicks", "show_preview", "og_title", "og_description", "og_image",
              "webhook_url", "price_amount", "is_active"):
        v = getattr(data, f)
        if v is not None:
            setattr(l, f, v)
    if data.trackers is not None:
        l.trackers = json.dumps(data.trackers.model_dump())
    if data.tags is not None:
        _sync_tags(db, l.owner, link=l, names=data.tags)
    db.commit()
    db.refresh(l)
    await invalidate_link(code)
    return link_to_out(l)


@router.delete("/{code}")
async def delete_link(code: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    l = db.query(Link).filter(Link.code == code).first()
    if not l or (l.owner_id != user.id and not user.is_admin):
        raise HTTPException(404, "Ссылка не найдена")
    db.delete(l)
    db.commit()
    await invalidate_link(code)
    return {"ok": True}
