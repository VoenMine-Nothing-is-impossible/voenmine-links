"""Платный доступ: создание платежа YooKassa + webhook подтверждения."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import create_paid_token
from ..config import settings
from ..database import get_db
from ..metrics import PAYMENTS
from ..models import Link, Payment
from ..payments import create_payment

router = APIRouter(tags=["payments"])


@router.post("/api/links/{code}/pay")
async def pay_for_link(code: str, request: Request, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.code == code).first()
    if not link or not link.price_amount:
        raise HTTPException(404, "Оплата не требуется")
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    desc = f"Доступ к ссылке {code}"
    ret = f"{base}/{code}"
    data = await create_payment(link.price_amount, desc, ret)
    pay = Payment(link_id=link.id, amount=link.price_amount,
                  currency=link.price_currency or "RUB",
                  yookassa_id=data.get("id"), status="pending",
                  payer_ip=request.client.host if request.client else "",
                  confirmation_url=data.get("confirmation_url"))
    db.add(pay)
    db.commit()
    try:
        PAYMENTS.labels(status="created").inc()
    except Exception:
        pass
    # MOCK-режим: сразу считаем оплаченным для локальной проверки
    if data.get("mock"):
        pay.status = "succeeded"
        db.commit()
        token = create_paid_token(code)
        resp = RedirectResponse(link.target_url, status_code=302)
        resp.set_cookie("paid", token, max_age=settings.PAID_TOKEN_EXPIRE_MINUTES * 60,
                        httponly=True, samesite="lax", path=f"/{code}")
        # также общий cookie для простоты проверки в go()
        resp.set_cookie("paid", token, max_age=settings.PAID_TOKEN_EXPIRE_MINUTES * 60,
                        httponly=True, samesite="lax", path="/")
        return resp
    if not data.get("confirmation_url"):
        raise HTTPException(502, "Платёжный провайдер не вернул ссылку на оплату")
    return {"confirmation_url": data["confirmation_url"], "payment_id": data["id"]}


@router.post("/api/payments/webhook")
async def yookassa_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook YooKassa: event payment.succeeded → помечаем платёж."""
    body = await request.json()
    obj = (body.get("object") or {})
    yid = obj.get("id")
    status = obj.get("status")
    if not yid:
        return {"ok": True}
    pay = db.query(Payment).filter(Payment.yookassa_id == yid).first()
    if pay and status == "succeeded":
        pay.status = "succeeded"
        db.commit()
        try:
            PAYMENTS.labels(status="succeeded").inc()
        except Exception:
            pass
    return {"ok": True}


@router.get("/pay/success/{code}")
def pay_success(code: str, db: Session = Depends(get_db)):
    """Ручное подтверждение (fallback, если webhook недоступен): выдаёт paid-cookie."""
    link = db.query(Link).filter(Link.code == code).first()
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    token = create_paid_token(code)
    resp = RedirectResponse(f"/{code}", status_code=302)
    resp.set_cookie("paid", token, max_age=settings.PAID_TOKEN_EXPIRE_MINUTES * 60,
                    httponly=True, samesite="lax", path="/")
    return resp
