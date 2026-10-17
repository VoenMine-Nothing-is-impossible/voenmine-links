"""VoenMine Links — точка входа FastAPI (порт 8096)."""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import Base, engine
from .limits import limiter
from .metrics import router as metrics_router
from .tasks import start_scheduler

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

log = logging.getLogger("links")

app = FastAPI(title="VoenMine Links", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- routers с префиксом /api — первыми ---
from .routers import apikeys as apikeys_router  # noqa: E402
from .routers import auth as auth_router  # noqa: E402
from .routers import links as links_router  # noqa: E402
from .routers import payments as payments_router  # noqa: E402
from .routers import stats as stats_router  # noqa: E402

app.include_router(auth_router.router)
app.include_router(links_router.router)
app.include_router(stats_router.router)
app.include_router(apikeys_router.router)
app.include_router(payments_router.router)
app.include_router(metrics_router)
# redirect-роутер (/{code}, /qr/...) — ПОСЛЕДНИМ, иначе перехватит /api/...
from .routers import redirect as redirect_router  # noqa: E402

app.include_router(redirect_router.router)


@app.on_event("startup")
def on_startup():
    try:
        from . import models  # noqa: F401 — регистрация таблиц

        Base.metadata.create_all(bind=engine)
    except Exception as e:  # noqa: BLE001
        log.warning("create_all failed: %s", e)
    try:
        start_scheduler()
    except Exception as e:  # noqa: BLE001
        log.warning("scheduler failed: %s", e)


@app.get("/health")
def health():
    return {"ok": True, "service": "voenmine-links"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "base_url": settings.PUBLIC_BASE_URL})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Не найдено"}, status_code=404)
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
