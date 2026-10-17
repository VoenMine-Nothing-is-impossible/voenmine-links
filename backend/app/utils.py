"""Валидация URL, генерация кодов, зарезервированные пути."""
import re
import secrets
import string
from urllib.parse import urlparse

RESERVED = {
    "api", "admin", "static", "login", "register", "logout", "dashboard",
    "docs", "openapi", "redoc", "metrics", "health", "qr", "q", "s", "l",
    "links", "assets", "_next", "favicon.ico", "robots.txt", "pay", "stats",
    "tags", "keys", "auth", "webhook", "payments", "preview", "expired",
}

SLUG_RE = re.compile(r"^[A-Z0-9]{7,64}$")
ALPHABET = string.ascii_uppercase + string.digits

BLOCKED_SCHEMES = {"javascript", "data", "file", "ftp", "vbscript", "blob"}


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if len(raw) > 4096:
        raise ValueError("URL слишком длинный")
    if not raw:
        raise ValueError("Пустой URL")
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme in BLOCKED_SCHEMES:
        raise ValueError(f"Запрещённая схема URL: {scheme}")
    if scheme not in ("http", "https"):
        raise ValueError("Разрешены только http(s) ссылки")
    if not parsed.netloc:
        raise ValueError("Некорректный URL (нет хоста)")
    return raw


def validate_slug(slug: str) -> str:
    slug = (slug or "").strip().upper()
    if not SLUG_RE.match(slug):
        raise ValueError("Алиас: минимум 7 символов, только A-Z и 0-9")
    if slug.lower() in RESERVED:
        raise ValueError(f"Алиас '{slug}' зарезервирован системой")
    return slug


def gen_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
