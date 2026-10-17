"""YooKassa: создание платежа через HTTP API (без тяжёлых SDK)."""
import uuid

import httpx

from .config import settings


async def create_payment(amount: float, description: str, return_url: str = "") -> dict:
    """Возвращает dict{id, confirmation_url, status}. В MOCK-режиме — фейк."""
    if settings.YOOKASSA_MOCK or not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        fake_id = "mock_" + uuid.uuid4().hex[:12]
        return {
            "id": fake_id,
            "confirmation_url": (return_url or settings.YOOKASSA_RETURN_URL or settings.PUBLIC_BASE_URL),
            "status": "pending",
            "mock": True,
        }
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
            headers={"Idempotence-Key": uuid.uuid4().hex},
            json={
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "capture": True,
                "confirmation": {"type": "redirect", "return_url": return_url or settings.PUBLIC_BASE_URL},
                "description": description[:128],
            },
        )
        r.raise_for_status()
        data = r.json()
        return {
            "id": data.get("id"),
            "confirmation_url": (data.get("confirmation") or {}).get("confirmation_url"),
            "status": data.get("status", "pending"),
            "mock": False,
        }
