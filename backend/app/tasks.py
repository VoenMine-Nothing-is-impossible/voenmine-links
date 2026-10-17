"""Фоновые задачи: чистка истёкших, health-check fallback, ретраи вебхуков."""
import datetime as dt
import json
import logging

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger("tasks")

_scheduler: BackgroundScheduler | None = None


def _local_imports():
    from .database import SessionLocal
    from .models import Link, WebhookDelivery
    return SessionLocal, Link, WebhookDelivery


def job_expire_links():
    try:
        SessionLocal, Link, _ = _local_imports()
        db = SessionLocal()
        try:
            now = dt.datetime.utcnow()
            rows = db.query(Link).filter(Link.is_active.is_(True), Link.expires_at.isnot(None),
                                        Link.expires_at <= now).all()
            for l in rows:
                l.is_active = False
            if rows:
                db.commit()
                log.info("expired %d links", len(rows))
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001
        log.warning("expire job failed: %s", e)


def job_healthcheck():
    """HEAD-проверка target_url у ссылок с fallback_url; при недоступности — health_ok=False."""
    try:
        SessionLocal, Link, _ = _local_imports()
        db = SessionLocal()
        try:
            links = db.query(Link).filter(Link.fallback_url.isnot(None), Link.is_active.is_(True)).limit(200).all()
            for l in links:
                try:
                    r = httpx.head(l.target_url, timeout=6, follow_redirects=True)
                    l.health_ok = r.status_code < 500
                except Exception:
                    l.health_ok = False
                l.last_health_at = dt.datetime.utcnow()
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001
        log.warning("health job failed: %s", e)


def job_webhook_retries(max_attempts: int = 5):
    try:
        SessionLocal, _, WebhookDelivery = _local_imports()
        db = SessionLocal()
        try:
            rows = db.query(WebhookDelivery).filter(
                WebhookDelivery.status == "pending", WebhookDelivery.attempts < max_attempts).limit(50).all()
            for w in rows:
                try:
                    payload = json.loads(w.payload or "{}")
                    r = httpx.post(w.target_url, json=payload, timeout=8)
                    w.attempts += 1
                    if 200 <= r.status_code < 300:
                        w.status = "ok"
                    else:
                        w.last_error = f"HTTP {r.status_code}"
                        if w.attempts >= max_attempts:
                            w.status = "failed"
                except Exception as e:  # noqa: BLE001
                    w.attempts += 1
                    w.last_error = str(e)[:500]
                    if w.attempts >= max_attempts:
                        w.status = "failed"
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001
        log.warning("webhook retry job failed: %s", e)


async def fire_webhook(target_url: str, payload: dict, db, link_id: int, click_id: int | None):
    """Быстрая попытка доставки + запись для ретраев."""
    from .models import WebhookDelivery
    rec = WebhookDelivery(link_id=link_id, click_id=click_id, target_url=target_url,
                          payload=json.dumps(payload, default=str), status="pending", attempts=0)
    db.add(rec)
    db.commit()
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.post(target_url, json=payload)
            rec.attempts = 1
            if 200 <= r.status_code < 300:
                rec.status = "ok"
            else:
                rec.last_error = f"HTTP {r.status_code}"
            db.commit()
    except Exception as e:  # noqa: BLE001
        rec.attempts = 1
        rec.last_error = str(e)[:500]
        db.commit()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    s = BackgroundScheduler()
    s.add_job(job_expire_links, "interval", minutes=5, id="expire")
    s.add_job(job_healthcheck, "interval", minutes=10, id="health")
    s.add_job(job_webhook_retries, "interval", minutes=2, id="webhooks")
    s.start()
    _scheduler = s
    return s
