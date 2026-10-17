"""Генерация QR-кодов (PNG/SVG) в локальный volume."""
import io
import os

import qrcode
import qrcode.image.svg

from .config import settings


def ensure_qr_dir():
    os.makedirs(settings.QR_DIR, exist_ok=True)
    return settings.QR_DIR


def short_url_for(code: str) -> str:
    return settings.PUBLIC_BASE_URL.rstrip("/") + "/" + code


def qr_png_bytes(code: str) -> bytes:
    url = short_url_for(code)
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def qr_svg_text(code: str) -> str:
    url = short_url_for(code)
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(url, image_factory=factory)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8", "ignore")
