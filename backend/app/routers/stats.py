from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_user
from ..database import get_db
from ..models import Click, Link, User

router = APIRouter(prefix="/api/links", tags=["stats"])


def _owned(db: Session, user: User, code: str) -> Link:
    l = db.query(Link).filter(Link.code == code).first()
    if not l or (l.owner_id != user.id and not user.is_admin):
        raise HTTPException(404, "Ссылка не найдена")
    return l


@router.get("/{code}/stats")
def link_stats(code: str, days: int = 30, db: Session = Depends(get_db),
               user: User = Depends(require_user)):
    link = _owned(db, user, code)
    clicks = db.query(Click).filter(Click.link_id == link.id).order_by(Click.ts.desc()).limit(5000).all()
    by_day: Counter = Counter()
    for c in clicks:
        by_day[str(c.ts.date()) if c.ts else "?"] += 1
    return {
        "code": code,
        "total": link.clicks_count,
        "events": len(clicks),
        "by_day": [{"date": d, "count": by_day[d]} for d in sorted(by_day)],
        "by_browser": dict(Counter(c.browser or "?" for c in clicks).most_common(10)),
        "by_os": dict(Counter(c.os or "?" for c in clicks).most_common(10)),
        "by_device": dict(Counter(c.device or "?" for c in clicks).most_common(10)),
        "by_country": dict(Counter(c.country or "?" for c in clicks).most_common(10)),
        "by_referrer": dict(Counter((c.referrer or "(прямой)")[:80] for c in clicks).most_common(10)),
        "last": [{"ts": str(c.ts), "ip": c.ip, "browser": c.browser, "os": c.os,
                  "device": c.device, "referrer": c.referrer} for c in clicks[:50]],
    }
