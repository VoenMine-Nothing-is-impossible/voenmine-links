"""Редирект /{code}: кэш, лимиты, пароль, превью, оплата, аналитика, вебхуки."""
import datetime as dt
import json

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..analytics import guess_country, parse_ua
from ..auth import check_paid_token, verify_password
from ..cache import get_cached_link, incr_click, invalidate_link, set_cached_link
from ..config import settings
from ..database import get_db
from ..limits import limiter
from ..metrics import CLICKS, REDIRECTS, WEBHOOKS
from ..models import Click, Link
from ..tasks import fire_webhook

router = APIRouter(tags=["redirect"])

from pathlib import Path as _Path
_TPL_DIR = str(_Path(__file__).resolve().parents[1] / "templates")
templates = Jinja2Templates(directory=_TPL_DIR)


def _expired_response(request: Request, link: Link | None):
    fallback = link.fallback_url if link and link.fallback_url else None
    return templates.TemplateResponse("expired.html", {
        "request": request, "link": link, "fallback": fallback,
        "base_url": settings.PUBLIC_BASE_URL,
    }, status_code=410)


def _trackers(link: Link) -> dict:
    try:
        return json.loads(link.trackers or "{}")
    except Exception:
        return {}


@router.get("/qr/{code}.png")
def qr_png(code: str, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from ..qrgen import qr_png_bytes
    if not db.query(Link).filter(Link.code == code).first():
        raise HTTPException(404, "Ссылка не найдена")
    return Response(content=qr_png_bytes(code), media_type="image/png")


@router.get("/qr/{code}.svg")
def qr_svg(code: str, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from ..qrgen import qr_svg_text
    if not db.query(Link).filter(Link.code == code).first():
        raise HTTPException(404, "Ссылка не найдена")
    return Response(content=qr_svg_text(code), media_type="image/svg+xml")


@router.get("/{code}", response_class=HTMLResponse)
@limiter.limit(f"{settings.RATE_REDIRECT_PER_MIN}/minute")
async def go(request: Request, code: str, db: Session = Depends(get_db),
             paid: str | None = Cookie(default=None)):
    if len(code) > 64 or "/" in code:
        raise HTTPException(404, "Ссылка не найдена")

    # 1) Redis-кэш горячих ссылок
    cached = await get_cached_link(code)
    link = db.query(Link).filter(Link.code == code).first()
    if not link:
        raise HTTPException(404, "Ссылка не найдена")

    # 2) Runtime-проверки: активна / срок / лимит
    now = dt.datetime.utcnow()
    if not link.is_active:
        return _expired_response(request, link)
    if link.expires_at and link.expires_at <= now:
        link.is_active = False
        db.commit()
        await invalidate_link(code)
        return _expired_response(request, link)
    if link.max_clicks is not None and link.clicks_count >= link.max_clicks:
        # пробуем резервный адрес
        if link.fallback_url:
            return RedirectResponse(link.fallback_url, status_code=302)
        return _expired_response(request, link)

    # 3) Пароль
    if link.password_hash:
        return templates.TemplateResponse("password.html", {
            "request": request, "code": code, "og_title": link.og_title,
            "trackers": _trackers(link),
        })

    # 4) Платный доступ
    if link.price_amount and link.price_amount > 0:
        if not (paid and check_paid_token(paid, code)):
            return templates.TemplateResponse("paywall.html", {
                "request": request, "code": code,
                "amount": link.price_amount, "currency": link.price_currency or "RUB",
                "og_title": link.og_title, "trackers": _trackers(link),
            })

    # 5) Превью перед редиректом
    if link.show_preview:
        return templates.TemplateResponse("preview.html", {
            "request": request, "code": code, "link": link,
            "target": link.target_url, "trackers": _trackers(link),
        })

    await _do_redirect(request, db, link)
    dest = link.target_url
    if link.health_ok is False and link.fallback_url:
        dest = link.fallback_url
    return RedirectResponse(dest, status_code=302)


@router.post("/{code}/unlock", response_class=HTMLResponse)
async def unlock_password(request: Request, code: str, password: str = Form(...),
                          db: Session = Depends(get_db),
                          paid: str | None = Cookie(default=None)):
    from ..auth import check_paid_token as _check_paid
    link = db.query(Link).filter(Link.code == code).first()
    if not link or not link.password_hash:
        raise HTTPException(404, "Ссылка не найдена")
    if not verify_password(password, link.password_hash):
        return templates.TemplateResponse("password.html", {
            "request": request, "code": code, "error": "Неверный пароль",
            "trackers": _trackers(link),
        }, status_code=403)
    # пароль верный → дальше по цепочке: оплата → превью → редирект
    if link.price_amount and link.price_amount > 0:
        if not (paid and _check_paid(paid, code)):
            return templates.TemplateResponse("paywall.html", {
                "request": request, "code": code,
                "amount": link.price_amount, "currency": link.price_currency or "RUB",
                "og_title": link.og_title, "trackers": _trackers(link),
            })
    if link.show_preview:
        return templates.TemplateResponse("preview.html", {
            "request": request, "code": code, "link": link,
            "target": link.target_url, "trackers": _trackers(link),
        })
    await _do_redirect(request, db, link)
    dest = link.target_url
    if link.health_ok is False and link.fallback_url:
        dest = link.fallback_url
    return RedirectResponse(dest, status_code=302)


@router.post("/{code}/continue", response_class=HTMLResponse)
async def continue_after_preview(request: Request, code: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.code == code).first()
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    await _do_redirect(request, db, link)
    dest = link.target_url
    if link.health_ok is False and link.fallback_url:
        dest = link.fallback_url
    return RedirectResponse(dest, status_code=302)


async def _do_redirect(request: Request, db: Session, link: Link):
    """Атомарный инкремент + запись клика + вебхук. Кэш обновляется."""
    code = link.code
    # Redis atomic incr (защита от гонок)
    await incr_click(code)
    link.clicks_count = (link.clicks_count or 0) + 1

    ua = request.headers.get("user-agent", "")
    browser, os, device = parse_ua(ua)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or \
        (request.client.host if request.client else "")
    ref = request.headers.get("referer", "")
    click = Click(link_id=link.id, ip=ip[:64], country=guess_country(ip),
                  user_agent=ua[:1000], browser=browser, os=os, device=device,
                  referrer=ref[:1000])
    db.add(click)
    db.commit()
    db.refresh(click)

    try:
        CLICKS.inc()
        REDIRECTS.labels(code=code).inc()
    except Exception:
        pass

    # вебхук на клик (фоновая доставка + ретраи через scheduler)
    if link.webhook_url:
        payload = {"code": code, "ts": dt.datetime.utcnow().isoformat() + "Z",
                   "ip": ip, "country": click.country, "user_agent": ua,
                   "browser": browser, "os": os, "device": device, "referrer": ref,
                   "target": link.target_url, "click_id": click.id}
        try:
            await fire_webhook(link.webhook_url, payload, db, link.id, click.id)
            WEBHOOKS.labels(status="queued").inc()
        except Exception:
            pass

    await set_cached_link(code, {"target": link.target_url, "clicks": link.clicks_count})
