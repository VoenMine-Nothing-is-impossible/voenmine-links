ВНИМАНИЕ!!  Этот репозиторий создан с помощью ИИ. Все распространяется "как есть", проект не несет ответственность за работоспособность кода.



# VoenMine Links — сократитель ссылок (self-hosted)

Аналог linkary.ru для своего домена. Backend FastAPI на порту 8096 за Traefik, Postgres + Redis, опциональный Next.js-фронт.

## Состав

```
.
├── docker-compose.yml   # app (8096) + postgres + redis + frontend(профиль)
├── .env.example
├── backend/
│   ├── Dockerfile       # alembic upgrade head + uvicorn :8096
│   ├── alembic.ini, alembic/env.py, alembic/versions/0001_initial.py
│   ├── requirements.txt
│   └── app/
│       ├── main.py      # /, /login, /register, /dashboard, /health, /metrics
│       ├── models.py    # users, links, tags, clicks, payments, webhooks
│       ├── routers/     # auth, links, stats, apikeys, payments, redirect
│       ├── templates/   # тёмная тема, пилюли-функции, password/paywall/preview/expired
│       └── static/      # style.css, app.js
└── frontend/            # Next.js (тёмная тема, те же пилюли, кабинет)
    ├── Dockerfile, package.json, next.config.js
    └── pages/ index, login, register, dashboard
```

## Функции (все из ТЗ)

 1. Сокращение + валидация (normalize_url блокирует javascript:, data:, file:, ftp:…).
 2. Дедупликация: повторное создание той же ссылки с теми же параметрами (expires, лимит, пароль, цена, превью, вебхук, fallback, OG, трекеры, теги) возвращает тот же код.
 3. Своё окончание: ^\[A-Z0-9\]{7,64}$, автогенерация из A-Z0-9 длиной 7, резерв (api, admin, static…).
 4. Срок жизни: runtime-проверка + APScheduler гасит истёкшие каждые 5 мин → страница 410.
 5. Лимит переходов: Redis INCR (атомарно) + clicks_count в PG; после лимита — expired/fallback.
 6. Пароль: промежуточная форма, хеш bcrypt.
 7. Платный доступ: YooKassa POST /api/links/{code}/pay, redirect на confirmation, webhook payment.succeeded, paid-cookie (JWT). YOOKASSA_MOCK=true — мгновенная выдача для теста.
 8. Метки: tags + фильтр ?tag= в кабинете.
 9. Превью/OG: show_preview, og_title/description/image + meta-теги; цепочка пароль → оплата → превью → 302.
10. Вебхук на клик: POST {ts, ip, geo, UA, referrer…}, запись в webhook_deliveries, ретраи ×5 каждые 2 мин.
11. QR: GET /qr/{code}.png|.svg, скачивание.
12. Трекеры: GA/FB/YM/GTM вставляются на password/paywall/preview; встроенная аналитика GET /api/links/{code}/stats (по дням, гео, браузеры, ОС, устройства, referrer).
13. Кабинет: JWT регистрация/вход, фильтры по статусу/метке/поиску, PATCH/DELETE, статистика, API-ключи lm\_… (Bearer).
14. API: POST/GET/PATCH/DELETE /api/links, /api/keys, /metrics (Prometheus), /health, rate-limit slowapi.

## Запуск

```bash
cp .env.example .env   # заполнить DOMAIN, SECRET_KEY, POSTGRES_PASSWORD, YOOKASSA_*
docker compose up -d --build
docker compose logs -f app
```

- Backend/UI: http://SERVER:8096 (или https://DOMAIN через Traefik).
- API docs: /api/docs. Фронт Next.js: docker compose --profile frontend up -d → :8097.

## Traefik

На app уже висят labels (Host(${DOMAIN}), websecure, certresolver=le). Подключите внешнюю сеть proxy при необходимости (заготовка закомментирована в compose).

## Футер

На всех страницах: ©2022 - 2026 VoenMine | Нет ничего невозможного!

