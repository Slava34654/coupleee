# Enrwine Server

FastAPI backend для Flutter-приложения Enrwine.

## Структура

- `backend/` - API, Telegram-бот, Alembic-миграции и тесты.
- `deploy/` - конфигурация production для systemd и reverse proxy.
- `android/` - только release APK и метаданные обновления приложения.
- `legacy/android-native/` - архив исходников старого Kotlin-клиента.
- `Dockerfile` и `fly.toml` - контейнерная сборка и Fly.io.

Рабочие `couple.db`, `photos/`, `.env` и service-account файлы не должны попадать в Git.

## Локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Swagger UI: `http://127.0.0.1:8000/docs`.

Для локальной БД и фото задайте `COUPLE_DB` и `PHOTO_DIR`. Без них backend использует `backend/couple.db` и `backend/photos/`.

## Тесты

```powershell
python -m pytest backend
```

Часть старых script-style тестов пока изменяет окружение при импорте. Их изоляция будет выполнена отдельным этапом; production БД для тестов использовать нельзя.

## Переменные окружения

Полный шаблон находится в `.env.example`. Основные группы:

- Хранилище: `COUPLE_DB`, `PHOTO_DIR`, S3-переменные и параметры `PHOTO_*`/`PHOTOS_PUBLIC_LEGACY`.
- Telegram и платежи: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_NAME`, `TELEGRAM_PROXY`, `PREMIUM_DAYS`, `PREMIUM_PRICE`, `PREMIUM_STARS`, `PAYMENT_URL`, `ADMIN_TG_IDS`, `REF_BONUS_DAYS`.
- Публичные URL: `APP_PUBLIC_URL`, `ANDROID_APK_URL`.
- Firebase: `FIREBASE_SERVICE_ACCOUNT_JSON`, `FIREBASE_SERVICE_ACCOUNT_BASE64`, `FIREBASE_SERVICE_ACCOUNT_FILE`.
- TMDB: `TMDB_API_KEY`, `TMDB_BEARER_TOKEN`, `TMDB_CATALOG_PAGES`, `TMDB_CACHE_TTL`.
- Runtime: `PORT`, `FORWARDED_ALLOW_IPS`, `ALLOW_INSECURE_EXACT_LOCATION`, `WS_AUTH_TIMEOUT_SECONDS`, `WS_MAX_MESSAGE_BYTES`.

Не коммитьте реальные значения. Production загружает их из `/etc/enrwine.env`.

## Flutter-клиент

Flutter-клиент хранится в отдельном соседнем checkout. Локальный Android-эмулятор обращается к backend по `http://10.0.2.2:8000/`.

## Production

Актуальная схема развёртывания описана в `README_DEPLOY.md`. Порядок security-миграции и совместимость клиентов описаны в `docs/MIGRATION.md`. Перед миграциями или операциями с данными сделайте внешний backup `couple.db` и `photos/`.
