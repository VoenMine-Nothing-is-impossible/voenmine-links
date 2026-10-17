from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

router = APIRouter()

REDIRECTS = Counter("links_redirects_total", "Всего редиректов", ["code"])
CREATED = Counter("links_created_total", "Всего созданных ссылок")
CLICKS = Counter("links_clicks_total", "Клики (инкременты)")
WEBHOOKS = Counter("links_webhooks_total", "Доставки вебхуков", ["status"])
PAYMENTS = Counter("links_payments_total", "Созданные платежи", ["status"])


@router.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
