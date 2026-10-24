"""Enrwine: Python-бэкенд (FastAPI + SQLite).
Запуск:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
Документация: http://127.0.0.1:8000/docs
"""

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    BackgroundTasks,
    Request,
)
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional
from typing import Optional, List, Literal
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
import hashlib
import hmac
import base64
import asyncio
import sqlite3
import datetime
import json
import math
import os
import random
import string
import tempfile
import time
import uuid
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen

try:
    from backend.movie_provider import MovieProviderError, TMDBMovieProvider
    from backend.community_map import COUNTRIES_BY_CODE, COUNTRY_CATALOG
except ImportError:
    from movie_provider import MovieProviderError, TMDBMovieProvider
    from community_map import COUNTRIES_BY_CODE, COUNTRY_CATALOG
try:
    from backend.companion_games import view as companion_game_view
    from backend.companion_games import care_together as companion_care_together
    from backend.companion_games import act as companion_game_act
    from backend.companion_games import buy_food as companion_buy_food
except ImportError:
    from companion_games import view as companion_game_view
    from companion_games import care_together as companion_care_together
    from companion_games import act as companion_game_act
    from companion_games import buy_food as companion_buy_food
try:
    from backend.database import upgrade_database
    from backend.db import connect, initialize
    from backend.time_utils import parse_utc, unix_ms, utc_iso, utc_now, utc_today
    from backend.config import *
    from backend.security import (
        AuthTokenMiddleware,
        DUMMY_PASSWORD_HASH,
        hash_password,
        hash_token,
        new_token,
        request_token,
        request_user,
        verify_password,
    )
except ImportError:
    from database import upgrade_database
    from db import connect, initialize
    from time_utils import parse_utc, unix_ms, utc_iso, utc_now, utc_today
    from config import *
    from security import (
        AuthTokenMiddleware,
        DUMMY_PASSWORD_HASH,
        hash_password,
        hash_token,
        new_token,
        request_token,
        request_user,
        verify_password,
    )
_ephemeral_photo_secret = EPHEMERAL_PHOTO_SECRET
_s3 = None
app = FastAPI(title="Enrwine API", version="1.0")
_request_token = request_token
_request_user = request_user


app.add_middleware(AuthTokenMiddleware)


def s3_configured() -> bool:
    return all((S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY))


def s3_client():
    global _s3
    if not s3_configured():
        return None
    if _s3 is None:
        import boto3
        from botocore.config import Config

        _s3 = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            region_name=S3_REGION,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
    return _s3


def s3_photo_key(name: str) -> str:
    return S3_PHOTO_PREFIX + os.path.basename(name)


# Static catalogs remain re-exported for compatibility with existing imports/tests.
try:
    from backend.seed.catalog import (
        IDEAS, MOVIES, MOVIE_GENRES, MOVIE_RATINGS, PACKS, QUESTIONS, QUESTIONS_EN,
        QUIZZES, QUIZ_CATEGORIES, generated_questions, movie_provider,
    )
except ImportError:
    from seed.catalog import (
        IDEAS, MOVIES, MOVIE_GENRES, MOVIE_RATINGS, PACKS, QUESTIONS, QUESTIONS_EN,
        QUIZZES, QUIZ_CATEGORIES, generated_questions, movie_provider,
    )


# ---------------- БД ----------------
def db():
    return connect(DB)


def init_db():
    initialize(
        DB,
        upgrade=upgrade_database,
        movie_genres=MOVIE_GENRES,
        quiz_categories=QUIZ_CATEGORIES,
        generated_questions=generated_questions,
        ideas=IDEAS,
        packs=PACKS,
        sql_placeholders=sql_placeholders,
        backfill_movie_matches=backfill_movie_matches,
    )


@app.on_event("startup")
def startup():
    init_db()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        try:
            from backend.bot import run_bot
        except ImportError:
            from bot import run_bot
        import threading

        threading.Thread(
            target=run_bot, args=(token,), daemon=True, name="tg-bot"
        ).start()


@app.get("/", include_in_schema=False)
def webapp():
    """Мобильное веб-приложение — открыть с телефона по IP компьютера."""
    return FileResponse(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")
    )


@app.get("/Enrwine.apk", include_in_schema=False)
def android_app():
    """Текущая Android-версия Enrwine для установки на телефон."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "android", "Enrwine.apk")
    if not os.path.isfile(path):
        path = os.path.join(root, "Enrwine.apk")
    if not os.path.isfile(path):
        raise HTTPException(404, "APK is not available")
    return FileResponse(
        path,
        media_type="application/vnd.android.package-archive",
        filename="Enrwine-latest.apk",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/app/version", include_in_schema=False)
def android_version(response: Response):
    """Metadata used by the Android in-app updater."""
    response.headers["Cache-Control"] = "no-store"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(root, "release.json"),
        os.path.join(root, "android", "release.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as release_file:
                release = json.load(release_file)
            return {
                "version": str(release["version"]),
                "build": int(release["build"]),
                "apk_url": str(release.get("apk_url", "/Enrwine.apk")),
                "notes": str(release.get("notes", "")),
            }
    raise HTTPException(404, "Release metadata is not available")


WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


@app.get("/manifest.webmanifest", include_in_schema=False)
def pwa_manifest():
    return FileResponse(
        os.path.join(WEB_DIR, "manifest.webmanifest"),
        media_type="application/manifest+json",
    )


@app.get("/sw.js", include_in_schema=False)
def pwa_sw():
    return FileResponse(
        os.path.join(WEB_DIR, "sw.js"), media_type="application/javascript"
    )


@app.get("/pet3d.html", include_in_schema=False)
def pet3d():
    """3D-питомец (Three.js): уход, комнаты, мини-игры. Прогресс хранится локально в браузере."""
    return FileResponse(os.path.join(WEB_DIR, "pet3d.html"), media_type="text/html")


# ---------------- реалтайм: WebSocket ----------------
class WSManager:
    def __init__(self):
        self.conns: dict = {}

    async def connect(self, ws, uid: int, *, accepted: bool = False):
        if not accepted:
            await ws.accept()
        self.conns.setdefault(uid, set()).add(ws)

    def drop(self, ws, uid: int):
        s = self.conns.get(uid)
        if s and ws in s:
            s.remove(ws)
            if not s:
                del self.conns[uid]

    async def send(self, uid: int, msg: dict):
        for ws in list(self.conns.get(uid, ())):
            try:
                await ws.send_json(msg)
            except Exception:
                pass

    async def ping_couple(self, uid: int, what: str = "all"):
        msg = {"type": "reload", "what": what}
        await self.send(uid, msg)
        try:
            me, partner = lookup_couple(uid)
        except HTTPException:
            return
        if partner:
            await self.send(partner["id"], msg)


wsman = WSManager()


@app.websocket("/ws")
async def ws_ep(ws: WebSocket):
    await ws.accept()
    try:
        raw_message = await asyncio.wait_for(
            ws.receive_text(), timeout=WS_AUTH_TIMEOUT_SECONDS
        )
    except TimeoutError:
        await ws.close(code=4408, reason="authentication timeout")
        return
    except WebSocketDisconnect:
        return
    if len(raw_message.encode("utf-8")) > WS_MAX_MESSAGE_BYTES:
        await ws.close(code=1009, reason="message too large")
        return
    try:
        message = json.loads(raw_message)
    except (TypeError, ValueError):
        await ws.close(code=1008, reason="invalid authentication message")
        return
    if not isinstance(message, dict) or message.get("type") != "auth":
        await ws.close(code=1008, reason="authentication required")
        return
    try:
        me = user_for_token(str(message.get("token") or ""))
    except HTTPException:
        await ws.close(code=4401, reason="unauthorized")
        return
    user_id = int(me["id"])
    _, partner = lookup_couple(user_id)
    await wsman.connect(ws, user_id, accepted=True)
    await ws.send_json({"type": "authenticated", "user_id": user_id})
    if partner:
        await wsman.send(
            partner["id"], {"type": "presence", "user_id": user_id, "online": True}
        )
    try:
        while True:
            try:
                raw_message = await asyncio.wait_for(
                    ws.receive_text(), timeout=WS_IDLE_TIMEOUT_SECONDS
                )
            except TimeoutError:
                await ws.close(code=4408, reason="idle timeout")
                break
            if len(raw_message.encode("utf-8")) > WS_MAX_MESSAGE_BYTES:
                await ws.close(code=1009, reason="message too large")
                break
            if raw_message == "ping":
                continue
            try:
                message = json.loads(raw_message)
            except (TypeError, ValueError):
                await ws.close(code=1008, reason="invalid message")
                break
            if message != {"type": "ping"}:
                await ws.close(code=1008, reason="unsupported message")
                break
    except WebSocketDisconnect:
        pass
    finally:
        wsman.drop(ws, user_id)
        if partner and user_id not in wsman.conns:
            await wsman.send(
                partner["id"], {"type": "presence", "user_id": user_id, "online": False}
            )


def today():
    return utc_today().isoformat()


SQL_IDENTIFIER_ALLOWLIST = frozenset(
    {
        "answers",
        "avatar",
        "community_map_posts",
        "companions",
        "couple_games",
        "events",
        "journal",
        "locations",
        "moods",
        "pack_a",
        "photo",
        "push_tokens",
        "qdate",
        "quiz_a",
        "taps",
        "users",
        "widget_photos",
        "wishlist",
    }
)
SQL_FRAGMENT_ALLOWLIST = frozenset(
    {
        "author_id=? OR pair_key=? OR pair_key LIKE ? OR pair_key LIKE ?",
        "pair_low_id=? OR pair_high_id=? OR created_by_user_id=?",
        "substr(ts,1,10)",
        "user_id=?",
    }
)


def sql_identifier(value: str) -> str:
    assert value in SQL_IDENTIFIER_ALLOWLIST, "SQL identifier is not allowed"
    return value


def sql_fragment(value: str) -> str:
    assert value in SQL_FRAGMENT_ALLOWLIST, "SQL fragment is not allowed"
    return value


def sql_placeholders(count: int) -> str:
    assert count > 0, "SQL value list must not be empty"
    return ",".join("?" for _ in range(count))


def lookup_couple(user_id: int):
    """Пара пользователя БЕЗ проверки токена — только для внутреннего
    использования (пинг WS, подсчёты), где запрос уже проверен выше."""
    con = db()
    me = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not me:
        con.close()
        raise HTTPException(404, "user not found")
    partner = None
    if me["partner_id"]:
        partner = con.execute(
            "SELECT * FROM users WHERE id=?", (me["partner_id"],)
        ).fetchone()
    con.close()
    return me, partner


def couple_of(user_id: int):
    """Пара пользователя + проверка токена текущего запроса.
    Токен выдаётся при создании/входе и хранится на устройстве.
    Без верного X-Auth-Token — 401 (id подряд не перебрать).
    """
    identity = _request_user.get()
    if identity:
        me, partner = identity
    else:
        me = authenticated_user()
        me, partner = lookup_couple(int(me["id"]))
    if int(me["id"]) != user_id:
        raise HTTPException(403, "token does not belong to user_id")
    return me, partner


def user_for_token(token: str):
    if not token:
        raise HTTPException(401, "unauthorized")
    con = db()
    user = con.execute(
        "SELECT * FROM users WHERE token_hash=?", (hash_token(token),)
    ).fetchone()
    con.close()
    if not user:
        raise HTTPException(401, "unauthorized")
    now_ms = unix_ms()
    if not user["token_expires_at"] or int(user["token_expires_at"]) <= now_ms:
        raise HTTPException(401, "token expired")
    return user


def authenticated_user():
    """Resolve the current session without trusting a caller-supplied user id."""
    return user_for_token(_request_token.get())


def current_user():
    me = authenticated_user()
    me, partner = lookup_couple(int(me["id"]))
    identity = (me, partner)
    _request_user.set(identity)
    return identity


protected = APIRouter(dependencies=[Depends(current_user)])

PUBLIC_HTTP_ROUTES = frozenset(
    {
        ("GET", "/"),
        ("GET", "/Enrwine.apk"),
        ("GET", "/app/version"),
        ("GET", "/manifest.webmanifest"),
        ("GET", "/sw.js"),
        ("GET", "/pet3d.html"),
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
        ("POST", "/pair"),
        ("POST", "/pair/join"),
        ("GET", "/health/push"),
        ("GET", "/health/bot"),
        ("GET", "/health/storage"),
        ("GET", "/quiz-categories"),
        ("GET", "/quiz-categories/{category_id}/subtopics"),
        ("GET", "/quizzes"),
        ("GET", "/ideas"),
        ("GET", "/idea/random"),
        ("POST", "/photos"),
        ("GET", "/photos/{name}"),
        ("GET", "/movies/poster/{filename}"),
    }
)


def audit_http_routes() -> frozenset[tuple[str, str]]:
    public_routes = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        requires_auth = any(
            dependency.call is current_user
            for dependency in route.dependant.dependencies
        )
        if not requires_auth:
            public_routes.update((method, route.path) for method in route.methods)
    observed = frozenset(public_routes)
    if observed != PUBLIC_HTTP_ROUTES:
        unexpected = sorted(observed - PUBLIC_HTTP_ROUTES)
        missing = sorted(PUBLIC_HTTP_ROUTES - observed)
        raise RuntimeError(
            f"HTTP route authorization audit failed: unexpected={unexpected}, "
            f"missing={missing}"
        )
    return observed


def partner_id_of(user_id: int) -> Optional[int]:
    me, partner = lookup_couple(user_id)
    return partner["id"] if partner else None


def touch_streak_days(user_id: int) -> int:
    """Серия дней, когда оба партнёра проявили хотя бы одну активность."""
    pid = partner_id_of(user_id)
    if pid is None:
        return 0
    con = db()

    def activity_days(uid: int):
        days = set()
        for table, date_expr in (
            ("answers", "qdate"),
            ("pack_a", "substr(ts,1,10)"),
            ("moods", "substr(ts,1,10)"),
            ("journal", "substr(ts,1,10)"),
        ):
            table = sql_identifier(table)
            date_expr = (
                sql_identifier(date_expr)
                if date_expr == "qdate"
                else sql_fragment(date_expr)
            )
            for row in con.execute(
                "SELECT DISTINCT "
                + date_expr
                + " d FROM "
                + table
                + " WHERE user_id=?",
                (uid,),
            ):
                days.add(row["d"])
        return days

    days = activity_days(user_id) & activity_days(pid)
    con.close()
    d = utc_today()
    if d.isoformat() not in days:
        d -= datetime.timedelta(days=1)
        if d.isoformat() not in days:
            return 0
    streak = 0
    while d.isoformat() in days:
        streak += 1
        d -= datetime.timedelta(days=1)
    return streak


try:
    from backend.models import *
except ImportError:
    from models import *


# ---------------- pairing / профиль ----------------
def new_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if len(value) > 254 or value.count("@") != 1:
        raise HTTPException(400, "invalid email")
    local, domain = value.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise HTTPException(400, "invalid email")
    return value


_DUMMY_PASSWORD_HASH = DUMMY_PASSWORD_HASH


def login_limit_keys(request: Request, email: str):
    client_ip = request.client.host if request.client else "unknown"
    return (
        ("email", hashlib.sha256(email.encode("utf-8")).hexdigest(), LOGIN_EMAIL_LIMIT),
        ("ip", hashlib.sha256(client_ip.encode("utf-8")).hexdigest(), LOGIN_IP_LIMIT),
    )


def login_retry_after(keys, now_ms: int) -> int:
    con = db()
    retry_after = 0
    try:
        for scope, key_hash, _ in keys:
            row = con.execute(
                "SELECT blocked_until FROM auth_login_limits "
                "WHERE scope=? AND key_hash=?",
                (scope, key_hash),
            ).fetchone()
            if row and row["blocked_until"] > now_ms:
                retry_after = max(
                    retry_after,
                    (row["blocked_until"] - now_ms + 999) // 1000,
                )
    finally:
        con.close()
    return retry_after


def record_failed_login(keys, now_ms: int) -> int:
    con = db()
    retry_after = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "DELETE FROM auth_login_limits "
            "WHERE blocked_until<? AND window_started_at<?",
            (now_ms - LOGIN_BLOCK_MS, now_ms - LOGIN_WINDOW_MS),
        )
        for scope, key_hash, limit in keys:
            row = con.execute(
                "SELECT failures,window_started_at,blocked_until "
                "FROM auth_login_limits WHERE scope=? AND key_hash=?",
                (scope, key_hash),
            ).fetchone()
            if not row or now_ms - row["window_started_at"] >= LOGIN_WINDOW_MS:
                failures = 1
                window_started_at = now_ms
                blocked_until = 0
            else:
                failures = row["failures"] + 1
                window_started_at = row["window_started_at"]
                blocked_until = row["blocked_until"]
            if failures >= limit:
                blocked_until = max(blocked_until, now_ms + LOGIN_BLOCK_MS)
                retry_after = max(retry_after, (blocked_until - now_ms + 999) // 1000)
            con.execute(
                "INSERT INTO auth_login_limits(scope,key_hash,failures,window_started_at,blocked_until) "
                "VALUES(?,?,?,?,?) ON CONFLICT(scope,key_hash) DO UPDATE SET "
                "failures=excluded.failures,window_started_at=excluded.window_started_at,"
                "blocked_until=excluded.blocked_until",
                (scope, key_hash, failures, window_started_at, blocked_until),
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return retry_after


def clear_login_limits(keys):
    con = db()
    try:
        con.executemany(
            "DELETE FROM auth_login_limits WHERE scope=? AND key_hash=?",
            [(scope, key_hash) for scope, key_hash, _ in keys],
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def raise_login_limit(retry_after: int):
    raise HTTPException(
        429,
        "too many login attempts",
        headers={"Retry-After": str(retry_after)},
    )


def auth_response(user, token: str):
    return {
        "user_id": user["id"],
        "pair_code": user["pair_code"],
        "partner_id": user["partner_id"],
        "token": token,
        "name": user["name"],
        "birth": user["birth"] or "",
        "avatar": user["avatar"] or "",
        "together_since": user["together_since"],
        "pair_ready": bool(user["pair_ready"]),
    }


def check_birth(birth: str) -> str:
    try:
        bd = datetime.date.fromisoformat(birth)
    except ValueError:
        raise HTTPException(400, "birth must be YYYY-MM-DD")
    if not (datetime.date(1900, 1, 1) <= bd <= utc_today()):
        raise HTTPException(400, "bad birth date")
    return birth


def age_of(birth: str):
    if not birth:
        return None
    b = datetime.date.fromisoformat(birth)
    t = utc_today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def check_since(since: str) -> str:
    """Дата начала отношений: YYYY-MM-DD, от 1900 до сегодня."""
    try:
        d = datetime.date.fromisoformat(since)
    except ValueError:
        raise HTTPException(400, "since must be YYYY-MM-DD")
    if not (datetime.date(1900, 1, 1) <= d <= utc_today()):
        raise HTTPException(400, "bad since date")
    return since


@app.post("/auth/register")
async def auth_register(body: AuthRegisterIn):
    email = normalize_email(body.email)
    password_hash = hash_password(body.password)
    con = db()
    try:
        if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(409, "email already registered")
        token = new_token()
        now_ms = unix_ms()
        expires_at = now_ms + TOKEN_TTL_MS
        cur = con.execute(
            "INSERT INTO users(name,pair_code,together_since,birth,avatar,token,token_hash,token_expires_at,email,password_hash,pair_ready) "
            "VALUES(?,?,?,?,?,'',?,?,?,?,0)",
            (
                email.split("@", 1)[0],
                new_code(),
                today(),
                "",
                "",
                hash_token(token),
                expires_at,
                email,
                password_hash,
            ),
        )
        uid = cur.lastrowid
        con.commit()
        user = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    except sqlite3.IntegrityError:
        con.rollback()
        raise HTTPException(409, "email already registered")
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    _request_token.set(token)
    return auth_response(user, token)


@app.post("/auth/login")
def auth_login(body: AuthLoginIn, request: Request):
    email = normalize_email(body.email)
    now_ms = unix_ms()
    keys = login_limit_keys(request, email)
    retry_after = login_retry_after(keys, now_ms)
    if retry_after:
        raise_login_limit(retry_after)
    con = db()
    user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    con.close()
    stored_hash = (
        user["password_hash"]
        if user and user["password_hash"]
        else _DUMMY_PASSWORD_HASH
    )
    password_in_range = 6 <= len(body.password) <= 128
    password_to_check = (
        body.password if len(body.password) <= 128 else body.password[:128]
    )
    password_valid = verify_password(password_to_check, stored_hash)
    if not user or not password_in_range or not password_valid:
        retry_after = record_failed_login(keys, now_ms)
        if retry_after:
            raise_login_limit(retry_after)
        raise HTTPException(401, "invalid email or password")
    clear_login_limits(keys)
    token = new_token()
    expires_at = now_ms + TOKEN_TTL_MS
    con = db()
    con.execute(
        "UPDATE users SET token='',token_hash=?,token_expires_at=? WHERE id=?",
        (hash_token(token), expires_at, user["id"]),
    )
    con.commit()
    user = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    con.close()
    _request_token.set(token)
    return auth_response(user, token)


def managed_photo_name(value: str) -> Optional[str]:
    if not value:
        return None
    path = urlparse(value).path
    marker = "/photos/"
    if marker not in path:
        return None
    name = path.rsplit(marker, 1)[-1]
    stem, extension = os.path.splitext(name)
    if extension.lower() not in {".jpg", ".png", ".gif", ".webp"}:
        return None
    try:
        uuid.UUID(hex=stem)
    except ValueError:
        return None
    return name


async def delete_managed_photos(names):
    client = s3_client()
    for name in names:
        path = os.path.join(PHOTO_DIR, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError as exc:
            print(f"Local photo deletion failed: {type(exc).__name__}")
        if client is not None:
            try:
                await run_in_threadpool(
                    client.delete_object,
                    Bucket=S3_BUCKET,
                    Key=s3_photo_key(name),
                )
            except Exception as exc:
                print(f"S3 photo deletion failed: {type(exc).__name__}")


def can_read_photo(name: str, user) -> bool:
    con = db()
    try:
        owned = con.execute(
            "SELECT 1 FROM photo_owners WHERE name=? AND user_id=?",
            (name, user["id"]),
        ).fetchone()
        if owned:
            return True
        if user["partner_id"]:
            partner_owned = con.execute(
                "SELECT 1 FROM photo_owners p JOIN users u ON u.id=p.user_id "
                "WHERE p.name=? AND u.id=? AND u.partner_id=?",
                (name, user["partner_id"], user["id"]),
            ).fetchone()
            if partner_owned:
                return True
        path = f"/photos/{name}"
        published = con.execute(
            "SELECT 1 FROM community_map_posts WHERE hidden=0 "
            "AND low_approved=1 AND high_approved=1 "
            "AND (photo=? OR photo LIKE ?) LIMIT 1",
            (path, f"%{path}"),
        ).fetchone()
        return bool(published)
    finally:
        con.close()


@protected.delete("/account")
async def delete_account(body: DeleteAccountIn):
    me, partner = couple_of(body.user_id)
    password_hash = me["password_hash"] or ""
    if password_hash:
        if not verify_password(body.password, password_hash):
            raise HTTPException(401, "invalid password")
    elif body.password != "DELETE":
        raise HTTPException(400, "enter DELETE to confirm")
    uid = me["id"]
    partner_id = partner["id"] if partner else None
    email_hash = hashlib.sha256((me["email"] or "").encode("utf-8")).hexdigest()
    pair_params = (str(uid), f"{uid}:%", f"%:{uid}")
    photo_names = set()
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        current = con.execute(
            "SELECT token_hash FROM users WHERE id=?", (uid,)
        ).fetchone()
        request_token = _request_token.get()
        if (
            not current
            or not request_token
            or not secrets.compare_digest(
                current["token_hash"] or "", hash_token(request_token)
            )
        ):
            raise HTTPException(401, "unauthorized")
        photo_values = [me["avatar"] or ""]
        for table, column, where, params in (
            ("journal", "photo", "user_id=?", (uid,)),
            ("pack_a", "photo", "user_id=?", (uid,)),
            ("widget_photos", "photo", "user_id=?", (uid,)),
            (
                "wishlist",
                "photo",
                "author_id=? OR pair_key=? OR pair_key LIKE ? OR pair_key LIKE ?",
                (uid, *pair_params),
            ),
            (
                "community_map_posts",
                "photo",
                "pair_low_id=? OR pair_high_id=? OR created_by_user_id=?",
                (uid, uid, uid),
            ),
        ):
            table = sql_identifier(table)
            column = sql_identifier(column)
            where = sql_fragment(where)
            photo_values.extend(
                row[column] or ""
                for row in con.execute(
                    "SELECT " + column + " FROM " + table + " WHERE " + where,
                    params,
                ).fetchall()
            )
        photo_names.update(
            name for value in photo_values if (name := managed_photo_name(value))
        )
        con.execute(
            "DELETE FROM journal_likes WHERE user_id=? OR entry_id IN "
            "(SELECT id FROM journal WHERE user_id=?)",
            (uid, uid),
        )
        con.execute(
            "DELETE FROM movie_swipes WHERE user_id=? OR round_id IN "
            "(SELECT id FROM movie_rounds WHERE pair_low_id=? OR pair_high_id=?)",
            (uid, uid, uid),
        )
        con.execute(
            "DELETE FROM movie_rounds WHERE pair_low_id=? OR pair_high_id=?",
            (uid, uid),
        )
        con.execute(
            "DELETE FROM community_map_comment_reports WHERE reporter_user_id=? "
            "OR comment_id IN (SELECT id FROM community_map_comments "
            "WHERE author_user_id=? OR post_id IN (SELECT id FROM community_map_posts "
            "WHERE pair_low_id=? OR pair_high_id=? OR created_by_user_id=?))",
            (uid, uid, uid, uid, uid),
        )
        con.execute(
            "DELETE FROM community_map_comments WHERE author_user_id=? OR post_id IN "
            "(SELECT id FROM community_map_posts WHERE pair_low_id=? OR pair_high_id=? "
            "OR created_by_user_id=?)",
            (uid, uid, uid, uid),
        )
        con.execute(
            "DELETE FROM community_map_likes WHERE user_id=? OR post_id IN "
            "(SELECT id FROM community_map_posts WHERE pair_low_id=? OR pair_high_id=? "
            "OR created_by_user_id=?)",
            (uid, uid, uid, uid),
        )
        con.execute(
            "DELETE FROM community_map_reports WHERE reporter_user_id=? OR post_id IN "
            "(SELECT id FROM community_map_posts WHERE pair_low_id=? OR pair_high_id=? "
            "OR created_by_user_id=?)",
            (uid, uid, uid, uid),
        )
        con.execute(
            "DELETE FROM community_map_posts WHERE pair_low_id=? OR pair_high_id=? "
            "OR created_by_user_id=?",
            (uid, uid, uid),
        )
        for table in ("wishlist", "couple_games", "companions"):
            table = sql_identifier(table)
            con.execute(
                "DELETE FROM " + table + " WHERE pair_key=? OR pair_key LIKE ? "
                "OR pair_key LIKE ?",
                pair_params,
            )
        con.execute("DELETE FROM wishlist WHERE author_id=?", (uid,))
        con.execute("DELETE FROM companions WHERE proposed_by=?", (uid,))
        con.execute(
            "DELETE FROM exact_widget_shares WHERE owner_id=? OR grantee_id=?",
            (uid, uid),
        )
        for table in (
            "moods",
            "answers",
            "quiz_a",
            "journal",
            "events",
            "pack_a",
            "taps",
            "widget_photos",
            "push_tokens",
            "locations",
        ):
            table = sql_identifier(table)
            con.execute("DELETE FROM " + table + " WHERE user_id=?", (uid,))
        telegram = con.execute(
            "SELECT tg_id FROM tg WHERE user_id=?", (uid,)
        ).fetchone()
        tg_id = telegram["tg_id"] if telegram else None
        con.execute(
            "DELETE FROM referral_rewards "
            "WHERE referrer_user_id=? OR referred_user_id=?",
            (uid, uid),
        )
        con.execute(
            "UPDATE referral_payouts SET user_id=0,recipient='' WHERE user_id=?",
            (uid,),
        )
        con.execute("DELETE FROM refs WHERE referrer=?", (uid,))
        con.execute(
            "UPDATE tg_payments SET user_id=0, tg_id=0, payload='' "
            "WHERE user_id=? OR tg_id=?",
            (uid, tg_id),
        )
        if tg_id is not None:
            con.execute("DELETE FROM refs WHERE tg_id=?", (tg_id,))
        con.execute("DELETE FROM tg WHERE user_id=?", (uid,))
        if me["email"]:
            con.execute(
                "DELETE FROM auth_login_limits WHERE scope='email' AND key_hash=?",
                (email_hash,),
            )
        con.execute(
            "UPDATE users SET partner_id=NULL,pair_ready=0 WHERE partner_id=?",
            (uid,),
        )
        deleted = con.execute("DELETE FROM users WHERE id=?", (uid,)).rowcount
        if deleted != 1:
            raise HTTPException(404, "user not found")
        retained_photos = []
        for table, column in (
            ("users", "avatar"),
            ("journal", "photo"),
            ("wishlist", "photo"),
            ("pack_a", "photo"),
            ("widget_photos", "photo"),
            ("community_map_posts", "photo"),
        ):
            table = sql_identifier(table)
            column = sql_identifier(column)
            retained_photos.extend(
                row[column] or ""
                for row in con.execute(
                    "SELECT " + column + " FROM " + table
                ).fetchall()
            )
        retained_names = {
            name for value in retained_photos if (name := managed_photo_name(value))
        }
        photo_names.difference_update(retained_names)
        con.executemany(
            "DELETE FROM photo_owners WHERE name=?",
            [(name,) for name in photo_names],
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    sockets = list(wsman.conns.pop(uid, ()))
    for socket in sockets:
        try:
            await socket.close(code=1000)
        except Exception:
            pass
    if partner_id is not None:
        await wsman.send(partner_id, {"type": "reload", "what": "account"})
    await delete_managed_photos(photo_names)
    _request_token.set("")
    return {"ok": True}


@protected.post("/pair/setup")
async def pair_setup(body: PairSetupIn):
    me, _ = couple_of(body.user_id)
    name = body.name.strip()
    if not name or len(name) > 80:
        raise HTTPException(400, "invalid name")
    if body.birth:
        check_birth(body.birth)
    con = db()
    partner = None
    try:
        if body.partner_code.strip():
            partner = con.execute(
                "SELECT * FROM users WHERE pair_code=? AND id!=?",
                (body.partner_code.strip().upper(), body.user_id),
            ).fetchone()
            if not partner or not partner["pair_ready"]:
                raise HTTPException(404, "code not found")
            if partner["partner_id"]:
                raise HTTPException(400, "code already used")
            since = partner["together_since"]
        else:
            since = check_since(body.since) if body.since else today()
        con.execute(
            "UPDATE users SET name=?,birth=?,avatar=?,together_since=?,partner_id=?,pair_ready=1 WHERE id=?",
            (
                name,
                body.birth,
                body.avatar,
                since,
                partner["id"] if partner else None,
                body.user_id,
            ),
        )
        if partner:
            con.execute(
                "UPDATE users SET partner_id=? WHERE id=?",
                (body.user_id, partner["id"]),
            )
        con.commit()
        user = con.execute("SELECT * FROM users WHERE id=?", (body.user_id,)).fetchone()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    if partner:
        await wsman.ping_couple(body.user_id, "pair")
    return auth_response(user, _request_token.get())


@app.post("/pair")
def pair_create(body: PairIn):
    if body.birth:
        check_birth(body.birth)
    since = check_since(body.since) if body.since else today()
    con = db()
    code = new_code()
    tok = new_token()
    expires_at = unix_ms() + TOKEN_TTL_MS
    cur = con.execute(
        "INSERT INTO users(name,pair_code,together_since,birth,avatar,token,token_hash,token_expires_at) "
        "VALUES(?,?,?,?,?,'',?,?)",
        (
            body.name.strip(),
            code,
            since,
            body.birth,
            body.avatar,
            hash_token(tok),
            expires_at,
        ),
    )
    con.commit()
    uid = cur.lastrowid
    con.close()
    _request_token.set(tok)
    return {"user_id": uid, "pair_code": code, "token": tok}


@app.post("/pair/join")
async def pair_join(body: JoinIn):
    if body.birth:
        check_birth(body.birth)
    con = db()
    other = con.execute(
        "SELECT * FROM users WHERE pair_code=?", (body.code.strip().upper(),)
    ).fetchone()
    if not other:
        con.close()
        raise HTTPException(404, "code not found")
    if other["partner_id"]:
        con.close()
        raise HTTPException(400, "code already used")
    tok = new_token()
    expires_at = unix_ms() + TOKEN_TTL_MS
    cur = con.execute(
        "INSERT INTO users(name,pair_code,together_since,birth,avatar,token,token_hash,token_expires_at) "
        "VALUES(?,?,?,?,?,'',?,?)",
        (
            body.name.strip(),
            new_code(),
            other["together_since"],
            body.birth,
            body.avatar,
            hash_token(tok),
            expires_at,
        ),
    )
    uid = cur.lastrowid
    con.execute("UPDATE users SET partner_id=? WHERE id=?", (uid, other["id"]))
    con.execute("UPDATE users SET partner_id=? WHERE id=?", (other["id"], uid))
    con.commit()
    con.close()
    _request_token.set(tok)
    await wsman.ping_couple(uid, "pair")
    return {"user_id": uid, "partner_id": other["id"], "token": tok}


@protected.get("/me")
def me(user_id: int):
    me, partner = couple_of(user_id)
    since = datetime.date.fromisoformat(me["together_since"])
    days = (utc_today() - since).days
    mine = None
    con = db()
    r = con.execute(
        "SELECT mood,note,ts FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if r:
        mine = dict(r)
    theirs = None
    if partner:
        r = con.execute(
            "SELECT mood,note,ts FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (partner["id"],),
        ).fetchone()
        if r:
            theirs = dict(r)
    con.close()
    return {
        "id": me["id"],
        "name": me["name"],
        "pair_code": me["pair_code"],
        "birth": me["birth"] or "",
        "avatar": me["avatar"] or "",
        "partner": (
            {
                "id": partner["id"],
                "name": partner["name"],
                "birth": partner["birth"] or "",
                "avatar": partner["avatar"] or "",
                "age": age_of(partner["birth"] or ""),
            }
            if partner
            else None
        ),
        "days_together": days,
        "together_since": me["together_since"],
        "streak": touch_streak_days(user_id),
        "my_mood": mine,
        "partner_mood": theirs,
    }


@protected.get("/partner")
def partner_profile(user_id: int):
    """Полный профиль партнёра: аватар, возраст, настроение, активность."""
    me, partner = couple_of(user_id)
    if not partner:
        raise HTTPException(400, "Партнёр ещё не добавлен")
    pid = partner["id"]
    con = db()
    mood = con.execute(
        "SELECT mood,note,ts FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (pid,),
    ).fetchone()
    answers = con.execute(
        "SELECT COUNT(*) n FROM answers WHERE user_id=?", (pid,)
    ).fetchone()["n"]
    answers += con.execute(
        "SELECT COUNT(*) n FROM pack_a WHERE user_id=?", (pid,)
    ).fetchone()["n"]
    moods = con.execute(
        "SELECT COUNT(*) n FROM moods WHERE user_id=?", (pid,)
    ).fetchone()["n"]
    moments = con.execute(
        "SELECT COUNT(*) n FROM journal WHERE user_id=?", (pid,)
    ).fetchone()["n"]
    taps = con.execute(
        "SELECT COUNT(*) n FROM taps WHERE user_id=?", (pid,)
    ).fetchone()["n"]
    con.close()
    return {
        "id": pid,
        "name": partner["name"],
        "avatar": partner["avatar"] or "",
        "birth": partner["birth"] or "",
        "age": age_of(partner["birth"] or ""),
        "days_together": (
            utc_today() - datetime.date.fromisoformat(me["together_since"])
        ).days,
        "latest_mood": dict(mood) if mood else None,
        "answers": answers,
        "moods": moods,
        "moments": moments,
        "taps": taps,
    }


@protected.post("/profile/avatar")
async def profile_avatar(body: AvatarIn):
    couple_of(body.user_id)
    avatar = body.avatar.strip()
    if len(avatar) > 2000:
        raise HTTPException(400, "avatar URL is too long")
    con = db()
    con.execute("UPDATE users SET avatar=? WHERE id=?", (avatar, body.user_id))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "profile")
    return {"ok": True}


# ---------------- push-уведомления ----------------
def firebase_messaging():
    """Инициализирует Firebase только при первой фактической отправке."""
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            encoded = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64", "").strip()
            path = os.environ.get(
                "FIREBASE_SERVICE_ACCOUNT_FILE",
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "firebase-service-account.json",
                ),
            )
            if encoded:
                value = json.loads(base64.b64decode(encoded).decode("utf-8"))
                firebase_admin.initialize_app(credentials.Certificate(value))
            elif raw:
                firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
            elif os.path.isfile(path):
                firebase_admin.initialize_app(credentials.Certificate(path))
            else:
                return None
        return messaging
    except Exception as exc:
        print(f"Firebase initialization failed: {type(exc).__name__}")
        return None


@app.get("/health/push", include_in_schema=False)
def push_health():
    return {"configured": firebase_messaging() is not None}


@app.get("/health/bot", include_in_schema=False)
def bot_health():
    configured = bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())
    if not configured:
        return {
            "configured": False,
            "running": False,
            "healthy": False,
            "last_poll": None,
            "last_error": "token_missing",
        }
    try:
        from backend.bot import bot_status
    except ImportError:
        from bot import bot_status
    return {"configured": True, **bot_status()}


def send_mood_push(user_id: int, partner_name: str, mood: str, note: str = ""):
    messaging = firebase_messaging()
    if messaging is None:
        return
    con = db()
    tokens = [
        r["token"]
        for r in con.execute(
            "SELECT token FROM push_tokens WHERE user_id=?", (user_id,)
        ).fetchall()
    ]
    con.close()
    invalid = []
    for token in tokens:
        try:
            messaging.send(
                messaging.Message(
                    notification=messaging.Notification(
                        title=f"Новое настроение от {partner_name}",
                        body=(
                            note[:80] if note else f"Партнёр выбрал настроение {mood}"
                        ),
                    ),
                    data={"type": "mood", "mood": mood},
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(sound="default"),
                    ),
                    token=token,
                )
            )
        except Exception as exc:
            if type(exc).__name__ in ("UnregisteredError", "SenderIdMismatchError"):
                invalid.append(token)
            else:
                print(f"Firebase send failed: {type(exc).__name__}")
    if invalid:
        con = db()
        con.executemany(
            "DELETE FROM push_tokens WHERE token=?", [(token,) for token in invalid]
        )
        con.commit()
        con.close()


def send_realtime_push(user_id: int, what: str):
    messaging = firebase_messaging()
    if messaging is None:
        return
    con = db()
    tokens = [
        r["token"]
        for r in con.execute(
            "SELECT token FROM push_tokens WHERE user_id=?", (user_id,)
        ).fetchall()
    ]
    con.close()
    invalid = []
    for token in tokens:
        try:
            messaging.send(
                messaging.Message(
                    data={"type": "reload", "what": what},
                    android=messaging.AndroidConfig(priority="high"),
                    token=token,
                )
            )
        except Exception as exc:
            if type(exc).__name__ in ("UnregisteredError", "SenderIdMismatchError"):
                invalid.append(token)
            else:
                print(f"Firebase send failed: {type(exc).__name__}")
    if invalid:
        con = db()
        con.executemany(
            "DELETE FROM push_tokens WHERE token=?", [(token,) for token in invalid]
        )
        con.commit()
        con.close()


@protected.post("/push/register")
def push_register(body: PushTokenIn):
    couple_of(body.user_id)
    token = body.token.strip()
    platform = body.platform.strip().lower()
    if not 20 <= len(token) <= 4096:
        raise HTTPException(400, "invalid push token")
    if platform not in ("android", "ios"):
        raise HTTPException(400, "invalid push platform")
    con = db()
    con.execute(
        "INSERT OR REPLACE INTO push_tokens(token,user_id,platform,updated_at) VALUES(?,?,?,?)",
        (
            token,
            body.user_id,
            platform,
            utc_iso(),
        ),
    )
    con.commit()
    con.close()
    return {"ok": True}


@protected.post("/push/unregister")
def push_unregister(body: PushTokenIn):
    couple_of(body.user_id)
    con = db()
    con.execute(
        "DELETE FROM push_tokens WHERE token=? AND user_id=?",
        (body.token.strip(), body.user_id),
    )
    con.commit()
    con.close()
    return {"ok": True}


# ---------------- настроение ----------------
@protected.post("/mood")
async def set_mood(body: MoodIn, background_tasks: BackgroundTasks):
    me, partner = couple_of(body.user_id)
    mood = body.mood.strip()
    note = body.note.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not mood and note:
        mood = "💬"
    if not mood:
        raise HTTPException(400, "mood or note is required")
    if len(mood) > 32:
        raise HTTPException(400, "mood is too long")
    if len(note) > 120:
        raise HTTPException(400, "mood message is too long")
    con = db()
    con.execute(
        "INSERT INTO moods(user_id,mood,note,ts) VALUES(?,?,?,?)",
        (
            body.user_id,
            mood,
            note,
            utc_iso(),
        ),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "mood")
    if partner:
        background_tasks.add_task(send_mood_push, partner["id"], me["name"], mood, note)
    return {"ok": True}


# ---------------- ежедневный вопрос ----------------
def daily_question():
    idx = utc_today().toordinal() % len(QUESTIONS)
    text_en = QUESTIONS_EN[idx] if idx < len(QUESTIONS_EN) else QUESTIONS[idx]
    return {"date": today(), "index": idx, "text": QUESTIONS[idx], "text_en": text_en}


def companion_daily_answer(user_id: int, answer: str):
    """Награждает питомца, когда оба партнёра ответили на вопрос дня."""
    partner_id = partner_id_of(user_id)
    if not partner_id:
        return False
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        pair_key = f"{min(user_id, partner_id)}:{max(user_id, partner_id)}"
        companion = con.execute(
            "SELECT state, version FROM companions WHERE pair_key=?", (pair_key,)
        ).fetchone()
        if not companion:
            return False
        import json

        state = json.loads(companion["state"])
        day = today()
        playground = state.setdefault("playground", {})
        if playground.get("daily_answer_day") != day:
            playground["daily_answer_day"] = day
            playground["daily_answer_users"] = []
            playground["daily_answer_rewarded"] = False
        answered = set(playground.get("daily_answer_users", []))
        if user_id in answered:
            return False
        answered.add(user_id)
        playground["daily_answer_users"] = list(answered)
        rewarded = len(answered) >= 2 and not playground["daily_answer_rewarded"]
        if rewarded:
            state["coins"] = int(state.get("coins", 0)) + 5
            state["bond"] = min(100, int(state.get("bond", 0)) + 1)
            state["joy"] = min(1.0, float(state.get("joy", 0)) + 0.05)
            playground["daily_answer_rewarded"] = True
        con.execute(
            "UPDATE companions SET state=?, version=?, updated_at=? WHERE pair_key=?",
            (
                json.dumps(state, ensure_ascii=False),
                companion["version"] + 1,
                utc_iso(),
                pair_key,
            ),
        )
        con.commit()
        return rewarded
    except Exception:
        con.rollback()
        return False
    finally:
        con.close()


@protected.get("/daily")
def get_daily(user_id: int):
    couple_of(user_id)
    dq = daily_question()
    con = db()
    pid = partner_id_of(user_id)
    mine = con.execute(
        "SELECT text FROM answers WHERE user_id=? AND qdate=?", (user_id, dq["date"])
    ).fetchone()
    theirs = (
        con.execute(
            "SELECT text FROM answers WHERE user_id=? AND qdate=?", (pid, dq["date"])
        ).fetchone()
        if pid
        else None
    )
    con.close()
    companion_reward = companion_daily_answer(user_id, mine["text"]) if mine else False
    return {
        "question": dq,
        "my_answer": mine["text"] if mine else None,
        "partner_answer": theirs["text"] if (mine and theirs) else None,
        "partner_answered": bool(theirs),
        "companion_reward": companion_reward,
    }


@protected.post("/daily/answer")
async def answer_daily(body: AnswerIn, background_tasks: BackgroundTasks):
    user_id = body.user_id
    me, partner = couple_of(user_id)
    dq = daily_question()
    con = db()
    con.execute(
        "INSERT OR REPLACE INTO answers(user_id,qdate,qindex,text,ts) VALUES(?,?,?,?,?)",
        (
            user_id,
            dq["date"],
            dq["index"],
            body.text,
            utc_iso(),
        ),
    )
    con.commit()
    con.close()
    companion_daily_answer(user_id, body.text)
    await wsman.ping_couple(user_id, "daily")
    if partner:
        background_tasks.add_task(send_realtime_push, partner["id"], "daily")
    return {"ok": True}


# ---------------- викторины ----------------
@app.get("/quiz-categories")
def quiz_categories():
    con = db()
    rows = con.execute("""
        SELECT c.id,c.title,COUNT(DISTINCT q.id) subtopics,COUNT(qq.id) questions
        FROM quiz_categories c
        LEFT JOIN quizzes q ON q.category_id=c.id
        LEFT JOIN quiz_q qq ON qq.quiz_id=q.id
        GROUP BY c.id,c.title,c.position
        ORDER BY c.position,c.id
    """).fetchall()
    con.close()
    return [dict(row) for row in rows]


@app.get("/quiz-categories/{category_id}/subtopics")
def quiz_subtopics(category_id: int):
    con = db()
    category = con.execute(
        "SELECT id,title FROM quiz_categories WHERE id=?", (category_id,)
    ).fetchone()
    if not category:
        con.close()
        raise HTTPException(404, "quiz category not found")
    rows = con.execute(
        """
        SELECT q.id,q.title,COUNT(qq.id) questions
        FROM quizzes q
        LEFT JOIN quiz_q qq ON qq.quiz_id=q.id
        WHERE q.category_id=?
        GROUP BY q.id,q.title,q.position
        ORDER BY q.position,q.id
    """,
        (category_id,),
    ).fetchall()
    con.close()
    return {
        "id": category["id"],
        "title": category["title"],
        "subtopics": [dict(row) for row in rows],
    }


@app.get("/quizzes")
def quizzes():
    con = db()
    rows = con.execute("""
        SELECT q.id,q.title,c.id category_id,c.title category_title
        FROM quizzes q
        LEFT JOIN quiz_categories c ON c.id=q.category_id
        ORDER BY c.position,q.position,q.id
    """).fetchall()
    out = []
    for r in rows:
        n = con.execute(
            "SELECT COUNT(*) n FROM quiz_q WHERE quiz_id=?", (r["id"],)
        ).fetchone()["n"]
        out.append(
            {
                "id": r["id"],
                "title": r["title"],
                "questions": n,
                "category_id": r["category_id"],
                "category_title": r["category_title"],
            }
        )
    con.close()
    return out


@protected.get("/quiz-progress")
def quiz_progress(user_id: int):
    me, partner = couple_of(user_id)
    if not partner:
        return {"quiz_ids": []}
    con = db()
    rows = con.execute(
        """
        SELECT DISTINCT mine.quiz_id
        FROM quiz_a mine
        JOIN quiz_a theirs
          ON theirs.quiz_id=mine.quiz_id AND theirs.qid=mine.qid
        WHERE mine.user_id=? AND theirs.user_id=?
        ORDER BY mine.quiz_id
    """,
        (me["id"], partner["id"]),
    ).fetchall()
    con.close()
    return {"quiz_ids": [row["quiz_id"] for row in rows]}


@protected.get("/quiz/{qid}")
def quiz(qid: int, user_id: int):
    couple_of(user_id)
    con = db()
    q = con.execute("SELECT * FROM quizzes WHERE id=?", (qid,)).fetchone()
    if not q:
        con.close()
        raise HTTPException(404, "quiz not found")
    rows = con.execute(
        "SELECT id,text,options FROM quiz_q WHERE quiz_id=? "
        "ORDER BY COALESCE(position,id),id",
        (qid,),
    ).fetchall()
    mine = {
        r["qid"]: r["option"]
        for r in con.execute(
            "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?",
            (user_id, qid),
        )
    }
    pid = partner_id_of(user_id)
    theirs = (
        {
            r["qid"]: True
            for r in con.execute(
                "SELECT qid FROM quiz_a WHERE user_id=? AND quiz_id=?", (pid, qid)
            )
        }
        if pid
        else {}
    )
    con.close()
    return {
        "id": q["id"],
        "title": q["title"],
        "questions": [
            {
                "id": r["id"],
                "text": r["text"],
                "options": json.loads(r["options"]),
                "my_option": mine.get(r["id"]),
                "partner_answered": r["id"] in theirs,
            }
            for r in rows
        ],
    }


@protected.post("/quiz/{qid}/answer")
async def quiz_answer(qid: int, body: QuizAnswerIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute(
        "SELECT id,options FROM quiz_q WHERE id=? AND quiz_id=?", (body.qid, qid)
    ).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "question not found")
    options = json.loads(ok["options"])
    if body.option < 0 or body.option >= len(options):
        con.close()
        raise HTTPException(400, "invalid option")
    con.execute(
        "INSERT OR REPLACE INTO quiz_a(user_id,quiz_id,qid,option) VALUES(?,?,?,?)",
        (body.user_id, qid, body.qid, body.option),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "quiz")
    return {"ok": True}


@protected.get("/quiz/{qid}/result")
def quiz_result(qid: int, user_id: int):
    me, partner = couple_of(user_id)
    if not partner:
        raise HTTPException(400, "Партнёр ещё не добавлен")
    con = db()
    rows = con.execute(
        "SELECT id,text,options FROM quiz_q WHERE quiz_id=? "
        "ORDER BY COALESCE(position,id),id",
        (qid,),
    ).fetchall()
    if not rows:
        con.close()
        raise HTTPException(404, "quiz not found")
    mine = {
        r["qid"]: r["option"]
        for r in con.execute(
            "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?",
            (user_id, qid),
        )
    }
    theirs = {
        r["qid"]: r["option"]
        for r in con.execute(
            "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?",
            (partner["id"], qid),
        )
    }
    common = [i for i in mine if i in theirs]
    completed = len(mine) == len(rows) and len(theirs) == len(rows)
    if not completed:
        con.close()
        return {
            "compatibility": None,
            "answered_together": len(common),
            "total": len(rows),
            "completed": False,
            "details": [],
        }
    details = []
    for row in rows:
        options = json.loads(row["options"])
        my_option = mine[row["id"]]
        partner_option = theirs[row["id"]]
        details.append(
            {
                "question_id": row["id"],
                "question": row["text"],
                "my_option": my_option,
                "partner_option": partner_option,
                "my_answer": (
                    options[my_option] if 0 <= my_option < len(options) else ""
                ),
                "partner_answer": (
                    options[partner_option]
                    if 0 <= partner_option < len(options)
                    else ""
                ),
                "matched": my_option == partner_option,
            }
        )
    con.close()
    same = sum(1 for item in details if item["matched"])
    return {
        "compatibility": round(100 * same / len(details)),
        "answered_together": len(common),
        "total": len(rows),
        "completed": True,
        "details": details,
    }


# ---------------- фото на виджет партнёра ----------------
@protected.post("/widget")
async def widget_send(body: WidgetIn, background_tasks: BackgroundTasks):
    me, partner = couple_of(body.user_id)
    if not body.photo:
        raise HTTPException(400, "empty photo")
    now = utc_iso()
    con = db()
    con.execute(
        "INSERT INTO widget_photos(user_id,photo,caption,ts) VALUES(?,?,?,?)",
        (body.user_id, body.photo, body.caption, now),
    )
    con.execute(
        "DELETE FROM widget_photos WHERE user_id=? AND id NOT IN "
        "(SELECT id FROM widget_photos WHERE user_id=? ORDER BY id DESC LIMIT 20)",
        (body.user_id, body.user_id),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "widget")
    if partner:
        background_tasks.add_task(send_realtime_push, partner["id"], "widget")
    return {"ok": True, "ts": now}


@protected.get("/widget")
def widget_latest(user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute(
        "SELECT photo,caption,ts FROM widget_photos WHERE user_id=? "
        "ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    theirs = (
        con.execute(
            "SELECT photo,caption,ts FROM widget_photos WHERE user_id=? "
            "ORDER BY id DESC LIMIT 1",
            (partner["id"],),
        ).fetchone()
        if partner
        else None
    )
    con.close()
    return {
        "mine": dict(mine) if mine else None,
        "partner": dict(theirs) if theirs else None,
    }


# ---------------- смена / удаление пары ----------------
@protected.delete("/pair")
async def pair_leave(user_id: int):
    """Покинуть пару, сохранив аккаунты и их действующие сессии."""
    me, partner = couple_of(user_id)
    con = db()
    pair_ids = tuple(sorted((user_id, partner["id"] if partner else user_id)))
    post_ids = con.execute(
        "SELECT id FROM community_map_posts WHERE pair_low_id=? AND pair_high_id=?",
        pair_ids,
    ).fetchall()
    for post in post_ids:
        community_map_delete_interactions(con, post["id"])
    con.execute(
        "DELETE FROM community_map_reports WHERE post_id IN "
        "(SELECT id FROM community_map_posts WHERE pair_low_id=? AND pair_high_id=?)",
        pair_ids,
    )
    con.execute(
        "DELETE FROM community_map_posts WHERE pair_low_id=? AND pair_high_id=?",
        pair_ids,
    )
    con.execute("UPDATE users SET partner_id=NULL,pair_ready=0 WHERE id=?", (user_id,))
    con.execute("DELETE FROM locations WHERE user_id=?", (user_id,))
    con.execute(
        "DELETE FROM exact_widget_shares WHERE owner_id=? OR grantee_id=?",
        (user_id, user_id),
    )
    if partner:
        con.execute(
            "UPDATE users SET partner_id=NULL,pair_ready=0 WHERE id=?", (partner["id"],)
        )
        con.execute("DELETE FROM locations WHERE user_id=?", (partner["id"],))
        con.execute(
            "DELETE FROM exact_widget_shares WHERE owner_id=? OR grantee_id=?",
            (partner["id"], partner["id"]),
        )
    con.commit()
    user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    msg = {"type": "reload", "what": "pair"}
    await wsman.send(user_id, msg)
    if partner:
        await wsman.send(partner["id"], msg)
    return auth_response(user, _request_token.get())


# ---------------- обнимашки (tap-to-feel) ----------------
@protected.post("/tap")
async def tap(body: TapIn):
    couple_of(body.user_id)
    now = utc_iso()
    con = db()
    con.execute("INSERT INTO taps(user_id,ts) VALUES(?,?)", (body.user_id, now))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "tap")
    return {"ok": True, "ts": now}


@protected.get("/tap")
def tap_status(user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute(
        "SELECT ts FROM taps WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    theirs = (
        con.execute(
            "SELECT ts FROM taps WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (partner["id"],),
        ).fetchone()
        if partner
        else None
    )
    n = con.execute(
        "SELECT COUNT(*) n FROM taps WHERE user_id IN (?,?)",
        (user_id, partner["id"] if partner else -1),
    ).fetchone()["n"]
    con.close()
    return {
        "my_last": mine["ts"] if mine else None,
        "partner_last": theirs["ts"] if theirs else None,
        "total": n,
    }


# ---------------- лента настроений ----------------
@protected.get("/moods")
def moods_feed(user_id: int):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    q = sql_placeholders(len(ids))
    con = db()
    rows = con.execute(
        "SELECT m.mood,m.note,m.ts,u.name author FROM moods m "
        "JOIN users u ON u.id=m.user_id WHERE m.user_id IN ("
        + q
        + ") ORDER BY m.id DESC LIMIT 14",
        ids,
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ---------------- активность партнёра ----------------
def timestamp_with_timezone(value: str) -> str:
    try:
        return parse_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (TypeError, ValueError):
        return value


@protected.get("/activity")
def partner_activity(user_id: int, limit: int = 50):
    _, partner = couple_of(user_id)
    if not partner:
        return {"partner_name": "", "items": []}
    limit = max(1, min(limit, 100))
    pid = partner["id"]
    con = db()
    items = []
    for r in con.execute(
        "SELECT id,mood,note,ts FROM moods WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit),
    ):
        items.append(
            {
                "id": f"mood:{r['id']}",
                "type": "mood",
                "ts": r["ts"],
                "detail": r["mood"],
                "extra": r["note"] or "",
                "photo": "",
            }
        )
    for r in con.execute(
        "SELECT qdate,qindex,ts FROM answers WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit),
    ):
        items.append(
            {
                "id": f"daily:{r['qdate']}:{r['qindex']}",
                "type": "daily",
                "ts": r["ts"],
                "detail": "",
                "extra": "",
                "photo": "",
            }
        )
    for r in con.execute(
        "SELECT a.pack_id,a.qid,a.ts,p.title FROM pack_a a "
        "JOIN packs p ON p.id=a.pack_id WHERE a.user_id=? ORDER BY a.ts DESC LIMIT ?",
        (pid, limit),
    ):
        items.append(
            {
                "id": f"pack:{r['pack_id']}:{r['qid']}",
                "type": "pack",
                "ts": r["ts"],
                "detail": r["title"],
                "extra": "",
                "photo": "",
            }
        )
    for r in con.execute(
        "SELECT id,title,photo,ts FROM journal WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit),
    ):
        items.append(
            {
                "id": f"journal:{r['id']}",
                "type": "journal",
                "ts": r["ts"],
                "detail": r["title"],
                "extra": "",
                "photo": r["photo"] or "",
            }
        )
    for r in con.execute(
        "SELECT id,ts FROM taps WHERE user_id=? ORDER BY ts DESC LIMIT ?", (pid, limit)
    ):
        items.append(
            {
                "id": f"tap:{r['id']}",
                "type": "tap",
                "ts": r["ts"],
                "detail": "",
                "extra": "",
                "photo": "",
            }
        )
    for r in con.execute(
        "SELECT id,photo,caption,ts FROM widget_photos WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit),
    ):
        items.append(
            {
                "id": f"widget:{r['id']}",
                "type": "widget",
                "ts": r["ts"],
                "detail": r["caption"] or "",
                "extra": "",
                "photo": r["photo"],
            }
        )
    con.close()
    items.sort(key=lambda item: item["ts"], reverse=True)
    for item in items:
        item["ts"] = timestamp_with_timezone(item["ts"])
    return {"partner_name": partner["name"], "items": items[:limit]}


# ---------------- статистика пары ----------------
@protected.get("/stats")
def stats(user_id: int):
    me, partner = couple_of(user_id)
    pid = partner["id"] if partner else None
    ids = [user_id] + ([pid] if pid else [])
    q = sql_placeholders(len(ids))
    con = db()
    answers = con.execute(
        "SELECT COUNT(*) n FROM answers WHERE user_id IN (" + q + ")", ids
    ).fetchone()["n"]
    answers += con.execute(
        "SELECT COUNT(*) n FROM pack_a WHERE user_id IN (" + q + ")", ids
    ).fetchone()["n"]
    moods = con.execute(
        "SELECT COUNT(*) n FROM moods WHERE user_id IN (" + q + ")", ids
    ).fetchone()["n"]
    moments = con.execute(
        "SELECT COUNT(*) n FROM journal WHERE user_id IN (" + q + ")", ids
    ).fetchone()["n"]
    compats = []
    if pid:
        for r in con.execute("SELECT id FROM quizzes").fetchall():
            qs = con.execute(
                "SELECT id FROM quiz_q WHERE quiz_id=?", (r["id"],)
            ).fetchall()
            ma = {
                x["qid"]: x["option"]
                for x in con.execute(
                    "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?",
                    (user_id, r["id"]),
                )
            }
            ta = {
                x["qid"]: x["option"]
                for x in con.execute(
                    "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?",
                    (pid, r["id"]),
                )
            }
            common = [i for i in ma if i in ta]
            if common:
                compats.append(
                    100 * sum(1 for i in common if ma[i] == ta[i]) / len(common)
                )
    con.close()
    return {
        "days_together": (
            utc_today() - datetime.date.fromisoformat(me["together_since"])
        ).days,
        "streak": touch_streak_days(user_id),
        "answers": answers,
        "moods": moods,
        "moments": moments,
        "avg_compatibility": round(sum(compats) / len(compats)) if compats else None,
        "quizzes_together": len(compats),
    }


# ---------------- тематические паки вопросов ----------------
@protected.get("/packs")
def packs(user_id: int, kind: str = ""):
    me, partner = couple_of(user_id)
    pid = partner["id"] if partner else None
    con = db()
    rows = con.execute(
        "SELECT * FROM packs" + (" WHERE kind=?" if kind else ""),
        (kind,) if kind else [],
    ).fetchall()
    out = []
    for p in rows:
        total = con.execute(
            "SELECT COUNT(*) n FROM pack_q WHERE pack_id=?", (p["id"],)
        ).fetchone()["n"]
        my = con.execute(
            "SELECT COUNT(*) n FROM pack_a WHERE user_id=? AND pack_id=?",
            (user_id, p["id"]),
        ).fetchone()["n"]
        together = 0
        if pid:
            together = con.execute(
                "SELECT COUNT(*) n FROM pack_a a JOIN pack_a b "
                "ON a.pack_id=b.pack_id AND a.qid=b.qid "
                "WHERE a.user_id=? AND b.user_id=? AND a.pack_id=?",
                (user_id, pid, p["id"]),
            ).fetchone()["n"]
        out.append(
            {
                "id": p["id"],
                "title": p["title"],
                "description": p["description"],
                "kind": p["kind"],
                "total": total,
                "answered_by_me": my,
                "answered_together": together,
            }
        )
    con.close()
    return out


@protected.get("/pack/{pid}")
def pack(pid: int, user_id: int):
    me, partner = couple_of(user_id)
    paid = partner["id"] if partner else None
    con = db()
    p = con.execute("SELECT * FROM packs WHERE id=?", (pid,)).fetchone()
    if not p:
        con.close()
        raise HTTPException(404, "pack not found")
    rows = con.execute("SELECT id,text FROM pack_q WHERE pack_id=?", (pid,)).fetchall()
    mine = {
        r["qid"]: {"text": r["text"], "photo": r["photo"]}
        for r in con.execute(
            "SELECT qid,text,photo FROM pack_a WHERE user_id=? AND pack_id=?",
            (user_id, pid),
        )
    }
    theirs = (
        {
            r["qid"]: {"text": r["text"], "photo": r["photo"]}
            for r in con.execute(
                "SELECT qid,text,photo FROM pack_a WHERE user_id=? AND pack_id=?",
                (paid, pid),
            )
        }
        if paid
        else {}
    )
    con.close()
    return {
        "id": p["id"],
        "title": p["title"],
        "description": p["description"],
        "kind": p["kind"],
        "questions": [
            {
                "id": r["id"],
                "text": r["text"],
                "my_answer": (
                    mine.get(r["id"], {}).get("text") if r["id"] in mine else None
                ),
                "my_photo": (
                    mine.get(r["id"], {}).get("photo") if r["id"] in mine else None
                ),
                "partner_answered": r["id"] in theirs,
                "partner_answer": (
                    theirs[r["id"]]["text"]
                    if r["id"] in mine and r["id"] in theirs
                    else None
                ),
                "partner_photo": (
                    theirs[r["id"]]["photo"]
                    if r["id"] in mine and r["id"] in theirs
                    else None
                ),
            }
            for r in rows
        ],
    }


@protected.post("/pack/{pid}/answer")
async def pack_answer(pid: int, body: PackAnswerIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute(
        "SELECT id FROM pack_q WHERE id=? AND pack_id=?", (body.qid, pid)
    ).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "question not found")
    if not body.text and not body.photo:
        con.close()
        raise HTTPException(400, "empty answer")
    con.execute(
        "INSERT OR REPLACE INTO pack_a(user_id,pack_id,qid,text,photo,ts) VALUES(?,?,?,?,?,?)",
        (
            body.user_id,
            pid,
            body.qid,
            body.text,
            body.photo,
            utc_iso(),
        ),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "packs")
    return {"ok": True}


# ---------------- идеи свиданий ----------------
@app.get("/ideas")
def ideas(category: str = "", budget: str = ""):
    con = db()
    q, args = "SELECT * FROM ideas WHERE 1=1", []
    if category:
        q += " AND category=?"
        args.append(category)
    if budget:
        q += " AND budget=?"
        args.append(budget)
    rows = con.execute(q, args).fetchall()
    con.close()
    return [dict(r) for r in rows]


@app.get("/idea/random")
def idea_random():
    con = db()
    rows = con.execute("SELECT * FROM ideas WHERE done=0").fetchall()
    con.close()
    if not rows:
        raise HTTPException(404, "no ideas left")
    return dict(random.choice(rows))


@protected.post("/ideas")
async def idea_add(body: IdeaIn):
    con = db()
    cur = con.execute(
        "INSERT INTO ideas(title,category,budget) VALUES(?,?,?)",
        (body.title, body.category, body.budget),
    )
    con.commit()
    con.close()
    return {"id": cur.lastrowid}


@protected.post("/idea/{iid}/done")
async def idea_done(iid: int, done: bool = True):
    con = db()
    con.execute("UPDATE ideas SET done=? WHERE id=?", (1 if done else 0, iid))
    con.commit()
    con.close()
    return {"ok": True}


# ---------------- фото ----------------
def photo_extension(data: bytes):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return None


def photo_signing_secret() -> bytes:
    return PHOTO_URL_HMAC_SECRET or _ephemeral_photo_secret


def signed_photo_url(name: str, expires_at: int | None = None) -> str:
    expires_at = expires_at or int(time.time()) + S3_URL_TTL
    path = f"/photos/{name}"
    message = f"GET\n{path}\n{expires_at}".encode("utf-8")
    signature = hmac.new(photo_signing_secret(), message, hashlib.sha256).digest()
    encoded = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{path}?exp={expires_at}&sig={encoded}"


def valid_photo_signature(request: Request, name: str) -> bool:
    expires = request.query_params.getlist("exp")
    signatures = request.query_params.getlist("sig")
    if len(expires) != 1 or len(signatures) != 1:
        return False
    try:
        expires_at = int(expires[0])
    except ValueError:
        return False
    now = int(time.time())
    if expires_at < now or expires_at > now + S3_URL_TTL:
        return False
    expected = signed_photo_url(name, expires_at).rsplit("sig=", 1)[-1]
    return secrets.compare_digest(expected, signatures[0])


def photo_limit_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def apply_photo_upload_limit(
    con, scope: str, key_hash: str, limit: int, now_ms: int
) -> None:
    row = con.execute(
        "SELECT window_started_at_ms,issued FROM photo_upload_limits "
        "WHERE scope=? AND key_hash=?",
        (scope, key_hash),
    ).fetchone()
    if not row or now_ms - int(row["window_started_at_ms"]) >= PHOTO_UPLOAD_WINDOW_MS:
        con.execute(
            "INSERT OR REPLACE INTO photo_upload_limits"
            "(scope,key_hash,window_started_at_ms,issued) VALUES(?,?,?,1)",
            (scope, key_hash, now_ms),
        )
        return
    if int(row["issued"]) >= limit:
        retry_after = max(
            1,
            (PHOTO_UPLOAD_WINDOW_MS - (now_ms - int(row["window_started_at_ms"])))
            // 1000,
        )
        raise HTTPException(
            429, "too many photo uploads", headers={"Retry-After": str(retry_after)}
        )
    con.execute(
        "UPDATE photo_upload_limits SET issued=issued+1 "
        "WHERE scope=? AND key_hash=?",
        (scope, key_hash),
    )


@protected.post("/photos/upload-token")
def create_photo_upload_token(request: Request):
    user = authenticated_user()
    now_ms = unix_ms()
    today_utc = utc_today().isoformat()
    client_ip = request.client.host if request.client else "unknown"
    raw_token = secrets.token_urlsafe(32)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM photo_upload_tokens WHERE expires_at_ms<=?", (now_ms,))
        apply_photo_upload_limit(
            con,
            "user",
            photo_limit_key(str(user["id"])),
            PHOTO_UPLOAD_USER_LIMIT,
            now_ms,
        )
        apply_photo_upload_limit(
            con,
            "ip",
            photo_limit_key(client_ip),
            PHOTO_UPLOAD_IP_LIMIT,
            now_ms,
        )
        used_bytes = con.execute(
            "SELECT COALESCE(SUM(size_bytes),0) FROM photo_owners WHERE user_id=?",
            (user["id"],),
        ).fetchone()[0]
        if int(used_bytes) + PHOTO_MAX_BYTES > PHOTO_USER_QUOTA_BYTES:
            raise HTTPException(413, "photo storage quota exceeded")
        total_bytes = con.execute(
            "SELECT COALESCE(SUM(size_bytes),0) FROM photo_owners"
        ).fetchone()[0]
        if int(total_bytes) + PHOTO_MAX_BYTES > PHOTO_TOTAL_QUOTA_BYTES:
            raise HTTPException(507, "photo storage is full")
        usage = con.execute(
            "SELECT day_utc,day_uploaded_bytes FROM photo_upload_usage WHERE user_id=?",
            (user["id"],),
        ).fetchone()
        day_bytes = (
            int(usage["day_uploaded_bytes"])
            if usage and usage["day_utc"] == today_utc
            else 0
        )
        if day_bytes + PHOTO_MAX_BYTES > PHOTO_DAILY_BYTES:
            raise HTTPException(429, "daily photo upload quota exceeded")
        con.execute(
            "INSERT INTO photo_upload_tokens"
            "(token_hash,user_id,expires_at_ms,max_bytes,consumed_at_ms) "
            "VALUES(?,?,?,?,NULL)",
            (
                hash_token(raw_token),
                user["id"],
                now_ms + PHOTO_UPLOAD_TOKEN_TTL_MS,
                PHOTO_MAX_BYTES,
            ),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return {
        "upload_token": raw_token,
        "expires_at_ms": now_ms + PHOTO_UPLOAD_TOKEN_TTL_MS,
        "max_bytes": PHOTO_MAX_BYTES,
    }


def consume_photo_upload_token(raw_token: str):
    now_ms = unix_ms()
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        token_hash = hash_token(raw_token)
        token = con.execute(
            "SELECT user_id,max_bytes FROM photo_upload_tokens "
            "WHERE token_hash=? AND consumed_at_ms IS NULL AND expires_at_ms>?",
            (token_hash, now_ms),
        ).fetchone()
        if not token:
            raise HTTPException(401, "invalid or expired photo upload token")
        updated = con.execute(
            "UPDATE photo_upload_tokens SET consumed_at_ms=? "
            "WHERE token_hash=? AND consumed_at_ms IS NULL",
            (now_ms, token_hash),
        ).rowcount
        if updated != 1:
            raise HTTPException(401, "photo upload token already used")
        user = con.execute(
            "SELECT * FROM users WHERE id=?", (token["user_id"],)
        ).fetchone()
        con.commit()
        return user, int(token["max_bytes"])
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


async def stream_photo_to_temp(file: UploadFile, max_bytes: int) -> tuple[str, int, str]:
    os.makedirs(PHOTO_DIR, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        mode="w+b", prefix=".upload-", dir=PHOTO_DIR, delete=False
    )
    temp_path = temporary.name
    total = 0
    prefix = b""
    try:
        while chunk := await file.read(64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(400, f"max {max_bytes // (1024 * 1024)}MB")
            if len(prefix) < 16:
                prefix += chunk[: 16 - len(prefix)]
            await run_in_threadpool(temporary.write, chunk)
    except Exception:
        temporary.close()
        os.unlink(temp_path)
        raise
    temporary.close()
    extension = photo_extension(prefix)
    if extension is None:
        os.unlink(temp_path)
        raise HTTPException(400, "only jpeg/png/webp/gif images")
    return temp_path, total, extension


def apply_legacy_photo_upload_limits(request: Request, user) -> None:
    now_ms = unix_ms()
    client_ip = request.client.host if request.client else "unknown"
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        apply_photo_upload_limit(
            con,
            "user",
            photo_limit_key(str(user["id"])),
            PHOTO_UPLOAD_USER_LIMIT,
            now_ms,
        )
        apply_photo_upload_limit(
            con,
            "ip",
            photo_limit_key(client_ip),
            PHOTO_UPLOAD_IP_LIMIT,
            now_ms,
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@app.post("/photos")
async def upload_photo(request: Request, file: UploadFile = File(...)):
    upload_token = request.headers.get("x-photo-upload-token", "")
    if upload_token:
        user, max_bytes = consume_photo_upload_token(upload_token)
    elif PHOTO_UPLOAD_TOKEN_LEGACY:
        user = authenticated_user()
        apply_legacy_photo_upload_limits(request, user)
        max_bytes = PHOTO_MAX_BYTES
    else:
        raise HTTPException(401, "photo upload token required")
    temp_path, size_bytes, extension = await stream_photo_to_temp(file, max_bytes)
    name = uuid.uuid4().hex + extension
    client = s3_client()
    try:
        if client is None:
            await run_in_threadpool(
                os.replace, temp_path, os.path.join(PHOTO_DIR, name)
            )
            temp_path = ""
        else:
            content_types = {
                ".jpg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            await run_in_threadpool(
                client.upload_file,
                temp_path,
                S3_BUCKET,
                s3_photo_key(name),
                ExtraArgs={
                    "ContentType": content_types[extension],
                    "ServerSideEncryption": "AES256",
                },
            )
    except Exception as exc:
        print(f"S3 upload failed: {type(exc).__name__}")
        raise HTTPException(503, "photo storage unavailable")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        used_bytes = con.execute(
            "SELECT COALESCE(SUM(size_bytes),0) FROM photo_owners WHERE user_id=?",
            (user["id"],),
        ).fetchone()[0]
        if int(used_bytes) + size_bytes > PHOTO_USER_QUOTA_BYTES:
            raise HTTPException(413, "photo storage quota exceeded")
        total_bytes = con.execute(
            "SELECT COALESCE(SUM(size_bytes),0) FROM photo_owners"
        ).fetchone()[0]
        if int(total_bytes) + size_bytes > PHOTO_TOTAL_QUOTA_BYTES:
            raise HTTPException(507, "photo storage is full")
        today_utc = utc_today().isoformat()
        usage = con.execute(
            "SELECT day_utc,day_uploaded_bytes FROM photo_upload_usage WHERE user_id=?",
            (user["id"],),
        ).fetchone()
        day_bytes = (
            int(usage["day_uploaded_bytes"])
            if usage and usage["day_utc"] == today_utc
            else 0
        )
        if day_bytes + size_bytes > PHOTO_DAILY_BYTES:
            raise HTTPException(429, "daily photo upload quota exceeded")
        con.execute(
            "INSERT INTO photo_owners(name,user_id,created_at,size_bytes) VALUES(?,?,?,?)",
            (
                name,
                user["id"],
                utc_iso(),
                size_bytes,
            ),
        )
        con.execute(
            "INSERT INTO photo_upload_usage(user_id,day_utc,day_uploaded_bytes) "
            "VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET "
            "day_uploaded_bytes=CASE WHEN day_utc=excluded.day_utc "
            "THEN day_uploaded_bytes+excluded.day_uploaded_bytes "
            "ELSE excluded.day_uploaded_bytes END,day_utc=excluded.day_utc",
            (user["id"], today_utc, size_bytes),
        )
        con.commit()
    except Exception:
        con.rollback()
        await delete_managed_photos([name])
        raise
    finally:
        con.close()
    url = f"/photos/{name}"
    return {"url": url, "signed_url": signed_photo_url(name)}


@app.get("/photos/{name}")
def get_photo(name: str, request: Request):
    if managed_photo_name(f"/photos/{name}") != name:
        raise HTTPException(404, "not found")
    if not valid_photo_signature(request, name) and not PHOTOS_PUBLIC_LEGACY:
        user = authenticated_user()
        if not can_read_photo(name, user):
            raise HTTPException(404, "not found")
    private_headers = {"Cache-Control": "private, no-store"}
    path = os.path.join(PHOTO_DIR, os.path.basename(name))
    if os.path.isfile(path):
        return FileResponse(path, headers=private_headers)
    client = s3_client()
    if client is None:
        raise HTTPException(404, "not found")
    try:
        result = client.get_object(Bucket=S3_BUCKET, Key=s3_photo_key(name))
        stream = result["Body"]
    except Exception as exc:
        error = getattr(exc, "response", {}).get("Error", {})
        if error.get("Code") in {"NoSuchKey", "404"}:
            raise HTTPException(404, "not found")
        print(f"S3 download failed: {type(exc).__name__}")
        raise HTTPException(503, "photo storage unavailable")
    def body_chunks():
        try:
            while chunk := stream.read(64 * 1024):
                yield chunk
        finally:
            stream.close()

    return StreamingResponse(
        body_chunks(),
        media_type=result.get("ContentType") or "application/octet-stream",
        headers=private_headers,
    )


@app.get("/health/storage", include_in_schema=False)
def storage_health():
    client = s3_client()
    if client is None:
        return {"configured": False, "mode": "local", "healthy": True}
    try:
        client.head_bucket(Bucket=S3_BUCKET)
        return {"configured": True, "mode": "s3", "healthy": True}
    except Exception as exc:
        return {
            "configured": True,
            "mode": "s3",
            "healthy": False,
            "error": type(exc).__name__,
        }


# ---------------- журнал ----------------
@protected.post("/journal")
async def journal_add(body: JournalIn):
    couple_of(body.user_id)
    con = db()
    cur = con.execute(
        "INSERT INTO journal(user_id,title,text,photo,ts) VALUES(?,?,?,?,?)",
        (
            body.user_id,
            body.title,
            body.text,
            body.photo,
            utc_iso(),
        ),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "journal")
    return {"id": cur.lastrowid}


def journal_row(r, user_id: int, con) -> dict:
    likes = con.execute(
        "SELECT COUNT(*) n FROM journal_likes WHERE entry_id=?", (r["id"],)
    ).fetchone()["n"]
    liked = con.execute(
        "SELECT 1 FROM journal_likes WHERE entry_id=? AND user_id=?", (r["id"], user_id)
    ).fetchone()
    d = dict(r)
    d["likes"] = likes
    d["liked_by_me"] = bool(liked)
    return d


@protected.get("/journal")
def journal_list(user_id: int, q: str = "", author: str = "all", fav: bool = False):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    sql = (
        "SELECT j.*,u.name author FROM journal j JOIN users u ON u.id=j.user_id "
        f"WHERE j.user_id IN ({','.join('?' * len(ids))})"
    )
    args: list = list(ids)
    if author == "me":
        sql += " AND j.user_id=?"
        args.append(user_id)
    elif author == "partner" and partner:
        sql += " AND j.user_id=?"
        args.append(partner["id"])
    if fav:
        sql += " AND j.fav=1"
    if q:
        sql += " AND (j.title LIKE ? OR j.text LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY j.fav DESC, j.id DESC"
    con = db()
    rows = con.execute(sql, args).fetchall()
    out = [journal_row(r, user_id, con) for r in rows]
    con.close()
    return out


@protected.post("/journal/{jid}/like")
async def journal_like(jid: int, body: LikeIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute("SELECT id,user_id FROM journal WHERE id=?", (jid,)).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "entry not found")
    had = con.execute(
        "SELECT 1 FROM journal_likes WHERE entry_id=? AND user_id=?",
        (jid, body.user_id),
    ).fetchone()
    if had:
        con.execute(
            "DELETE FROM journal_likes WHERE entry_id=? AND user_id=?",
            (jid, body.user_id),
        )
        liked = False
    else:
        con.execute(
            "INSERT INTO journal_likes(entry_id,user_id) VALUES(?,?)",
            (jid, body.user_id),
        )
        liked = True
    likes = con.execute(
        "SELECT COUNT(*) n FROM journal_likes WHERE entry_id=?", (jid,)
    ).fetchone()["n"]
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "journal")
    return {"liked": liked, "likes": likes}


@protected.post("/journal/{jid}/fav")
async def journal_fav(jid: int, body: LikeIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute("SELECT fav FROM journal WHERE id=?", (jid,)).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "entry not found")
    con.execute("UPDATE journal SET fav=? WHERE id=?", (0 if ok["fav"] else 1, jid))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "journal")
    return {"ok": True}


@protected.delete("/journal/{jid}")
async def journal_del(jid: int, user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    row = con.execute("SELECT user_id FROM journal WHERE id=?", (jid,)).fetchone()
    if not row:
        con.close()
        raise HTTPException(404, "entry not found")
    if row["user_id"] != user_id:
        con.close()
        raise HTTPException(403, "only author can delete")
    con.execute("DELETE FROM journal_likes WHERE entry_id=?", (jid,))
    con.execute("DELETE FROM journal WHERE id=?", (jid,))
    con.commit()
    con.close()
    await wsman.ping_couple(user_id, "journal")
    return {"ok": True}


# ---------------- события / обратный отсчёт ----------------
def next_annual(month: int, day: int, now: datetime.date) -> datetime.date:
    for y in range(now.year, now.year + 9):
        try:
            d = datetime.date(y, month, day)
        except ValueError:
            continue  # 29 февраля
        if d >= now:
            return d
    return datetime.date(now.year + 1, month, day)


@protected.post("/events")
async def event_add(body: EventIn):
    couple_of(body.user_id)
    datetime.date.fromisoformat(body.date)  # проверка формата
    con = db()
    cur = con.execute(
        "INSERT INTO events(user_id,title,date,icon,repeat) VALUES(?,?,?,?,?)",
        (body.user_id, body.title, body.date, body.icon, 1 if body.repeat else 0),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "events")
    return {"id": cur.lastrowid}


@protected.get("/events")
def events(user_id: int):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    q = sql_placeholders(len(ids))
    con = db()
    rows = con.execute(
        "SELECT * FROM events WHERE user_id IN (" + q + ")", ids
    ).fetchall()
    con.close()
    now = utc_today()
    out = []
    for r in rows:
        base = datetime.date.fromisoformat(r["date"])
        show = r["date"]
        if r["repeat"]:
            nxt = next_annual(base.month, base.day, now)
            d = (nxt - now).days
            show = nxt.isoformat()
        else:
            d = (base - now).days
        out.append(
            {
                "id": r["id"],
                "title": r["title"],
                "date": show,
                "days_left": d,
                "icon": r["icon"] or "🎉",
                "repeat": bool(r["repeat"]),
            }
        )
    out.sort(
        key=lambda e: (
            e["days_left"] < 0,
            abs(e["days_left"]) if e["days_left"] >= 0 else -e["days_left"],
        )
    )
    return out


@protected.delete("/events/{eid}")
async def event_del(eid: int, user_id: int):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    con = db()
    row = con.execute("SELECT user_id FROM events WHERE id=?", (eid,)).fetchone()
    if not row:
        con.close()
        raise HTTPException(404, "event not found")
    if row["user_id"] not in ids:
        con.close()
        raise HTTPException(403, "not your event")
    con.execute("DELETE FROM events WHERE id=?", (eid,))
    con.commit()
    con.close()
    await wsman.ping_couple(user_id, "events")
    return {"ok": True}


# ---------------- общий вишлист пары ----------------
def wishlist_couple(user_id: int):
    me, partner = couple_of(user_id)
    if not partner:
        raise HTTPException(400, "partner has not joined yet")
    key = f"{min(me['id'], partner['id'])}:{max(me['id'], partner['id'])}"
    return me, partner, key


def wishlist_row(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author_id": row["author_id"],
        "author": row["author"],
        "photo": row["photo"] or "",
        "done": bool(row["done"]),
        "created_at": row["created_at"],
        "completed_at": row["completed_at"] or "",
    }


@protected.get("/wishlist")
def wishlist_get(user_id: int):
    _, _, pair_key = wishlist_couple(user_id)
    con = db()
    rows = con.execute(
        "SELECT w.*, u.name author FROM wishlist w "
        "JOIN users u ON u.id=w.author_id WHERE w.pair_key=? "
        "ORDER BY w.done, w.created_at DESC, w.id DESC",
        (pair_key,),
    ).fetchall()
    con.close()
    return [wishlist_row(row) for row in rows]


@protected.post("/wishlist")
async def wishlist_add(body: WishlistIn):
    _, _, pair_key = wishlist_couple(body.user_id)
    title = body.title.strip()
    if not title or len(title) > 200:
        raise HTTPException(400, "title must contain 1 to 200 characters")
    photo = body.photo.strip()
    if len(photo) > 2000:
        raise HTTPException(400, "photo URL is too long")
    created_at = utc_iso()
    con = db()
    cur = con.execute(
        "INSERT INTO wishlist(pair_key,author_id,title,photo,created_at) VALUES(?,?,?,?,?)",
        (pair_key, body.user_id, title, photo, created_at),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "wishlist")
    return {"id": cur.lastrowid}


@protected.post("/wishlist/{item_id}/done")
async def wishlist_done(item_id: int, body: WishlistDoneIn):
    _, _, pair_key = wishlist_couple(body.user_id)
    con = db()
    row = con.execute(
        "SELECT id FROM wishlist WHERE id=? AND pair_key=?", (item_id, pair_key)
    ).fetchone()
    if not row:
        con.close()
        raise HTTPException(404, "wishlist item not found")
    completed_at = (
        utc_iso() if body.done else ""
    )
    con.execute(
        "UPDATE wishlist SET done=?,completed_at=? WHERE id=?",
        (1 if body.done else 0, completed_at, item_id),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "wishlist")
    return {"ok": True}


@protected.delete("/wishlist/{item_id}")
async def wishlist_delete(item_id: int, user_id: int):
    _, _, pair_key = wishlist_couple(user_id)
    con = db()
    row = con.execute(
        "SELECT id FROM wishlist WHERE id=? AND pair_key=?", (item_id, pair_key)
    ).fetchone()
    if not row:
        con.close()
        raise HTTPException(404, "wishlist item not found")
    con.execute("DELETE FROM wishlist WHERE id=?", (item_id,))
    con.commit()
    con.close()
    await wsman.ping_couple(user_id, "wishlist")
    return {"ok": True}


# ---------------- расстояние между партнёрами ----------------
# Приватность: хранится только последняя точка каждого (округлена до ~100 м),
# координаты партнёра клиенту НЕ отдаются — только расстояние. Работает лишь когда
# делятся оба. Выключение (DELETE /location) стирает точку.
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def minutes_ago(ts: str) -> Optional[int]:
    try:
        then = parse_utc(ts)
    except ValueError:
        return None
    return max(0, int((utc_now() - then).total_seconds() // 60))


def exact_location_transport_is_secure(request: Request) -> bool:
    if os.environ.get("ALLOW_INSECURE_EXACT_LOCATION") == "1":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    return (forwarded or request.url.scheme).lower() == "https"


def require_secure_exact_location(request: Request):
    if not exact_location_transport_is_secure(request):
        raise HTTPException(426, "HTTPS required for exact location")


@protected.post("/location")
async def location_set(body: LocationIn, request: Request):
    _, partner = couple_of(body.user_id)  # 404, если пользователя нет
    if (
        not math.isfinite(body.lat)
        or not math.isfinite(body.lon)
        or not (-90 <= body.lat <= 90 and -180 <= body.lon <= 180)
    ):
        raise HTTPException(400, "bad coordinates")
    now = utc_iso()
    con = db()
    con.execute(
        "INSERT OR REPLACE INTO locations(user_id,lat,lon,ts) VALUES(?,?,?,?)",
        (body.user_id, round(body.lat, 3), round(body.lon, 3), now),
    )
    if (
        partner
        and partner["partner_id"] == body.user_id
        and exact_location_transport_is_secure(request)
    ):
        con.execute(
            "UPDATE exact_widget_shares SET lat=?,lon=?,location_ts=? "
            "WHERE owner_id=? AND grantee_id=?",
            (body.lat, body.lon, now, body.user_id, partner["id"]),
        )
    con.commit()
    con.close()
    return {"ok": True}


@protected.delete("/location")
def location_stop(user_id: int):
    couple_of(user_id)
    con = db()
    con.execute("DELETE FROM locations WHERE user_id=?", (user_id,))
    con.execute("DELETE FROM exact_widget_shares WHERE owner_id=?", (user_id,))
    con.commit()
    con.close()
    return {"ok": True}


@protected.post("/widget/location/consent")
def exact_widget_consent_grant(body: ExactWidgetConsentIn, request: Request):
    require_secure_exact_location(request)
    _, partner = couple_of(body.user_id)
    if partner is None or partner["partner_id"] != body.user_id:
        raise HTTPException(409, "reciprocal partner required")
    now = utc_iso()
    con = db()
    con.execute(
        "INSERT OR REPLACE INTO exact_widget_shares("
        "owner_id,grantee_id,lat,lon,location_ts,consented_at) "
        "VALUES(?,?,NULL,NULL,NULL,?)",
        (body.user_id, partner["id"], now),
    )
    con.commit()
    con.close()
    return {"ok": True}


@protected.delete("/widget/location/consent")
def exact_widget_consent_revoke(user_id: int):
    couple_of(user_id)
    con = db()
    con.execute("DELETE FROM exact_widget_shares WHERE owner_id=?", (user_id,))
    con.commit()
    con.close()
    return {"ok": True}


@protected.get("/widget/location")
def exact_widget_location(user_id: int, request: Request):
    require_secure_exact_location(request)
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute(
        "SELECT lat,lon,location_ts FROM exact_widget_shares WHERE owner_id=?",
        (user_id,),
    ).fetchone()
    theirs = None
    if partner is not None and partner["partner_id"] == user_id:
        theirs = con.execute(
            "SELECT lat,lon,location_ts FROM exact_widget_shares "
            "WHERE owner_id=? AND grantee_id=?",
            (partner["id"], user_id),
        ).fetchone()
    con.close()
    distance_km = None
    if (
        mine is not None
        and theirs is not None
        and mine["lat"] is not None
        and mine["lon"] is not None
        and theirs["lat"] is not None
        and theirs["lon"] is not None
    ):
        distance_km = round(
            haversine_km(mine["lat"], mine["lon"], theirs["lat"], theirs["lon"]),
            2,
        )
    return {
        "sharing": mine is not None,
        "partner_sharing": theirs is not None,
        "my_name": me["name"],
        "my_lat": mine["lat"] if mine else None,
        "my_lon": mine["lon"] if mine else None,
        "my_updated_at": mine["location_ts"] if mine else None,
        "my_age_min": (
            minutes_ago(mine["location_ts"])
            if mine and mine["location_ts"]
            else None
        ),
        "partner_name": partner["name"] if partner else None,
        "lat": theirs["lat"] if theirs else None,
        "lon": theirs["lon"] if theirs else None,
        "updated_at": theirs["location_ts"] if theirs else None,
        "age_min": (
            minutes_ago(theirs["location_ts"])
            if theirs and theirs["location_ts"]
            else None
        ),
        "km": distance_km,
    }


@protected.get("/distance")
def distance(user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute(
        "SELECT lat,lon,ts FROM locations WHERE user_id=?", (user_id,)
    ).fetchone()
    theirs = (
        con.execute(
            "SELECT lat,lon,ts FROM locations WHERE user_id=?", (partner["id"],)
        ).fetchone()
        if partner
        else None
    )
    con.close()
    out = {
        "sharing": mine is not None,
        "partner_sharing": theirs is not None,
        "km": None,
        "partner_name": partner["name"] if partner else None,
        "partner_age_min": minutes_ago(theirs["ts"]) if theirs else None,
    }
    if mine is not None and theirs is not None:
        out["km"] = round(
            haversine_km(mine["lat"], mine["lon"], theirs["lat"], theirs["lon"]), 1
        )
    return out


# ---------------- подписка через Telegram-бота ----------------
def premium_active(premium_until: str) -> bool:
    try:
        return (
            bool(premium_until)
            and datetime.date.fromisoformat(premium_until) >= utc_today()
        )
    except ValueError:
        return False


def couple_premium_until(me, partner) -> str:
    active_until = []
    for user in (me, partner):
        if user is None or "premium_until" not in user.keys():
            continue
        until = user["premium_until"] or ""
        if premium_active(until):
            active_until.append(until)
    return max(active_until, default="")


@protected.get("/premium")
def premium_status(user_id: int):
    me, partner = couple_of(user_id)
    until = couple_premium_until(me, partner)
    email = me["email"] or "" if "email" in me.keys() else ""
    return {"premium": bool(until), "until": until, "email": email}


# ---------------- общая дата «вместе с…» ----------------
# Единый счётчик для обоих: создатель задаёт при создании пары,
# потом любой из пары может поменять — меняется у обоих сразу.
class TogetherIn(BaseModel):
    user_id: int
    date: str  # YYYY-MM-DD


@protected.post("/together")
async def together_set(body: TogetherIn):
    me, partner = couple_of(body.user_id)
    date = check_since(body.date)
    con = db()
    con.execute("UPDATE users SET together_since=? WHERE id=?", (date, body.user_id))
    if partner:
        con.execute(
            "UPDATE users SET together_since=? WHERE id=?", (date, partner["id"])
        )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "pair")
    days = (utc_today() - datetime.date.fromisoformat(date)).days
    return {"date": date, "days": days}


# ---------------- общий питомец пары ----------------
COMPANION_ROOMS = {"rose": 0, "garden": 40, "night": 65, "beach": 90}


def companion_couple(user_id: int):
    me, partner = couple_of(user_id)
    if not partner:
        raise HTTPException(400, "partner has not joined yet")
    key = f"{min(me['id'], partner['id'])}:{max(me['id'], partner['id'])}"
    return me, partner, key


def fresh_companion():
    return {
        "type": "PET",
        "name": "",
        "adopted": False,
        "hunger": 0.72,
        "joy": 0.72,
        "energy": 0.8,
        "clean": 0.8,
        "bond": 0,
        "level": 1,
        "xp": 0,
        "coins": 20,
        "sleeping": False,
        "timestamp": 0,
        "lastAction": 0,
        "cooldowns": {},
        "day": "",
        "dailyActions": [],
        "rewardedDay": "",
        "careDay": "",
        "streak": 0,
        "room": "rose",
        "ownedRooms": ["rose"],
        "accessory": "none",
        "playground": {
            "care_day": "",
            "carers": [],
            "care_rewarded": False,
            "reward_day": "",
            "rewards": 0,
            "completed": 0,
            "badges": [],
            "album": [],
            "cloud_bests": {},
            "home": {},
        },
    }


def normalize_companion(value):
    state = fresh_companion()
    if isinstance(value, dict):
        state.update(value)
    state["type"] = state["type"] if state["type"] in ("PET", "BABY") else "PET"
    state["cooldowns"] = dict(state.get("cooldowns") or {})
    state["dailyActions"] = list(dict.fromkeys(state.get("dailyActions") or []))
    state["ownedRooms"] = list(dict.fromkeys(state.get("ownedRooms") or ["rose"]))
    playground = dict(state.get("playground") or {})
    playground.setdefault("care_day", "")
    playground.setdefault("carers", [])
    playground.setdefault("care_rewarded", False)
    playground.setdefault("reward_day", "")
    playground.setdefault("rewards", 0)
    playground.setdefault("completed", 0)
    playground.setdefault("badges", [])
    playground.setdefault("album", [])
    playground["cloud_bests"] = dict(playground.get("cloud_bests") or {})
    playground["home"] = dict(playground.get("home") or {})
    state["playground"] = playground
    return state


def companion_day(now_ms: int):
    return datetime.datetime.fromtimestamp(now_ms / 1000).date().isoformat()


def companion_advance(value, now_ms: int):
    state = normalize_companion(value)
    timestamp = int(state.get("timestamp") or 0)
    hours = (
        0 if not timestamp else min(max(now_ms - timestamp, 0), 24 * 3600000) / 3600000
    )
    sleeping = bool(state.get("sleeping"))
    state["hunger"] = min(
        1.0, max(0.12, float(state["hunger"]) - hours * (0.018 if sleeping else 0.035))
    )
    state["joy"] = min(1.0, max(0.15, float(state["joy"]) - hours * 0.022))
    state["clean"] = min(1.0, max(0.15, float(state["clean"]) - hours * 0.025))
    state["energy"] = min(
        1.0, max(0.12, float(state["energy"]) + hours * (0.4 if sleeping else -0.035))
    )
    state["timestamp"] = max(timestamp, now_ms)
    current_day = companion_day(now_ms)
    if state.get("day") != current_day:
        state["dailyActions"] = []
        if "playground" in state:
            state["playground"].update(
                care_day=current_day, carers=[], care_rewarded=False
            )
    state["day"] = current_day
    return state


def companion_required_xp(level: int):
    return 60 + level * 20


def companion_care(value, action: str, now_ms: int):
    state = companion_advance(value, now_ms)
    if not state["adopted"]:
        return state, "Сначала выберите малыша и имя", "idle"
    if now_ms - int(state.get("lastAction") or 0) < 2500:
        return state, "Подождите, малыш ещё занят", "idle"
    if action == "sleep":
        if not state["sleeping"] and float(state["energy"]) >= 0.95:
            return state, "Я уже выспался! Давайте поиграем", "idle"
        was_sleeping = bool(state["sleeping"])
        state["sleeping"] = not was_sleeping
        state["lastAction"] = now_ms
        return (
            state,
            (
                "Доброе утро!"
                if was_sleeping
                else "Тихий час · энергия растёт даже после закрытия приложения"
            ),
            ("love" if was_sleeping else "sleep"),
        )
    if state["sleeping"]:
        return state, "Сначала разбудите малыша — пусть откроет глазки", "idle"
    remaining = int(state["cooldowns"].get(action, 0)) - now_ms + 45000
    if remaining > 0:
        return (
            state,
            f"Ещё {(remaining + 999) // 1000} с — можно попробовать другое действие",
            "idle",
        )
    if action == "feed":
        if float(state["hunger"]) >= 0.92:
            return state, "Животик полон — покормите немного позже", "idle"
        state["hunger"] = min(1.0, float(state["hunger"]) + 0.25)
        state["joy"] = min(1.0, float(state["joy"]) + 0.03)
    elif action == "play":
        if float(state["energy"]) < 0.25:
            return state, "Сначала поспим: для игры нужна энергия", "idle"
        if float(state["hunger"]) < 0.2:
            return state, "Сначала перекусим, а потом поиграем", "idle"
        if float(state["joy"]) >= 0.95:
            return state, "Я счастлив! Давай немного отдохнём", "idle"
        state["joy"] = min(1.0, float(state["joy"]) + 0.24)
        state["energy"] = max(0.12, float(state["energy"]) - 0.12)
        state["hunger"] = max(0.12, float(state["hunger"]) - 0.07)
        state["clean"] = max(0.15, float(state["clean"]) - 0.06)
    elif action == "wash":
        if float(state["clean"]) >= 0.95:
            return state, "Уже чистенький! Можно обнять", "idle"
        state["clean"] = 1.0
        state["joy"] = min(1.0, float(state["joy"]) + 0.04)
    elif action == "love":
        state["joy"] = min(1.0, float(state["joy"]) + 0.06)
        state["bond"] = min(100, int(state["bond"]) + 1)
    else:
        return state, "Неизвестное действие", "idle"
    current_day = companion_day(now_ms)
    yesterday = (
        datetime.datetime.fromtimestamp(now_ms / 1000).date()
        - datetime.timedelta(days=1)
    ).isoformat()
    actions = list(dict.fromkeys([*state["dailyActions"], action]))
    daily_reward = len(actions) >= 3 and state.get("rewardedDay") != current_day
    old_level = int(state["level"])
    state["xp"] = int(state["xp"]) + (3 if action == "love" else 10)
    state["coins"] = (
        int(state["coins"])
        + (0 if action == "love" else 2)
        + (15 if daily_reward else 0)
    )
    state["dailyActions"] = actions
    if daily_reward:
        state["rewardedDay"] = current_day
    if state.get("careDay") != current_day:
        state["streak"] = (
            int(state["streak"]) + 1 if state.get("careDay") == yesterday else 1
        )
    state["careDay"] = current_day
    state["cooldowns"][action] = now_ms
    state["lastAction"] = now_ms
    while int(state["level"]) < 10 and int(state["xp"]) >= companion_required_xp(
        int(state["level"])
    ):
        needed = companion_required_xp(int(state["level"]))
        state["xp"] = int(state["xp"]) - needed
        state["level"] = int(state["level"]) + 1
        state["coins"] = int(state["coins"]) + 20
    if int(state["level"]) == 10:
        state["xp"] = min(int(state["xp"]), companion_required_xp(10))
    if int(state["level"]) > old_level:
        message = f"Новый уровень {state['level']}! +20 монет · малыш подрос"
    elif daily_reward:
        message = "Забота дня выполнена! +15 монет"
    else:
        message = {
            "feed": "Ням! Спасибо за вкусный обед",
            "wash": "Пузырьки! Теперь я чистенький",
            "play": "Ура! Обожаю играть с тобой",
            "love": "Как хорошо рядом с тобой ♥",
        }[action]
    return state, message, action


def companion_response(
    row, state, version: int, user_id: int, message: str = "", animation: str = "idle"
):
    state = dict(state)
    state["playground"] = companion_game_view(
        state, user_id, companion_day(unix_ms()),
    )
    proposal = None
    if row and row["proposal_type"]:
        proposal = {
            "type": row["proposal_type"],
            "name": row["proposal_name"],
            "proposed_by": row["proposed_by"],
            "is_mine": row["proposed_by"] == user_id,
        }
    return {
        "state": state,
        "version": version,
        "proposal": proposal,
        "message": message,
        "animation": animation,
    }


@protected.get("/companion")
def companion_get(user_id: int):
    _, partner, pair_key = companion_couple(user_id)
    con = db()
    row = con.execute(
        "SELECT * FROM companions WHERE pair_key=?", (pair_key,)
    ).fetchone()
    con.close()
    state = (
        companion_advance(
            json.loads(row["state"]), unix_ms()
        )
        if row
        else fresh_companion()
    )
    return companion_response(row, state, row["version"] if row else 0, user_id)


@protected.post("/companion/propose")
async def companion_propose(body: CompanionProposalIn):
    _, partner, pair_key = companion_couple(body.user_id)
    pet_type = body.type.strip().upper()
    name = body.name.strip()
    if pet_type not in ("PET", "BABY"):
        raise HTTPException(400, "invalid companion type")
    if not name or len(name) > 24:
        raise HTTPException(400, "invalid companion name")
    con = db()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(
        "SELECT * FROM companions WHERE pair_key=?", (pair_key,)
    ).fetchone()
    state = normalize_companion(json.loads(row["state"])) if row else fresh_companion()
    if state["adopted"]:
        con.rollback()
        con.close()
        raise HTTPException(409, "companion already adopted")
    version = (row["version"] if row else 0) + 1
    now = utc_iso()
    con.execute(
        "INSERT OR REPLACE INTO companions(pair_key,state,proposal_type,proposal_name,proposed_by,version,updated_at) VALUES(?,?,?,?,?,?,?)",
        (pair_key, json.dumps(state), pet_type, name, body.user_id, version, now),
    )
    con.commit()
    row = con.execute(
        "SELECT * FROM companions WHERE pair_key=?", (pair_key,)
    ).fetchone()
    con.close()
    await wsman.ping_couple(body.user_id, "companion")
    return companion_response(
        row, state, version, body.user_id, "Предложение отправлено партнёру"
    )


@protected.post("/companion/confirm")
async def companion_confirm(body: CompanionUserIn):
    _, partner, pair_key = companion_couple(body.user_id)
    con = db()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(
        "SELECT * FROM companions WHERE pair_key=?", (pair_key,)
    ).fetchone()
    if not row or not row["proposal_type"]:
        con.rollback()
        con.close()
        raise HTTPException(409, "no companion proposal")
    if row["proposed_by"] == body.user_id:
        con.rollback()
        con.close()
        raise HTTPException(409, "partner must confirm the proposal")
    now_ms = unix_ms()
    state = fresh_companion()
    state.update(
        {
            "type": row["proposal_type"],
            "name": row["proposal_name"],
            "adopted": True,
            "timestamp": now_ms,
        }
    )
    version = row["version"] + 1
    con.execute(
        "UPDATE companions SET state=?,proposal_type='',proposal_name='',proposed_by=NULL,version=?,updated_at=? WHERE pair_key=?",
        (
            json.dumps(state),
            version,
            utc_iso(),
            pair_key,
        ),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "companion")
    return companion_response(
        None,
        state,
        version,
        body.user_id,
        f"{state['name']} теперь живёт у вас!",
        "love",
    )


@protected.post("/companion/action")
async def companion_action(body: CompanionActionIn):
    me, partner, pair_key = companion_couple(body.user_id)
    con = db()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(
        "SELECT * FROM companions WHERE pair_key=?", (pair_key,)
    ).fetchone()
    if not row:
        con.rollback()
        con.close()
        raise HTTPException(409, "choose a companion first")
    state = normalize_companion(json.loads(row["state"]))
    if not state["adopted"]:
        con.rollback()
        con.close()
        raise HTTPException(409, "choose a companion first")
    message, animation = "", "idle"
    now_ms = unix_ms()
    if body.action in ("feed", "play", "wash", "love", "sleep"):
        state, message, animation = companion_care(state, body.action, now_ms)
        if animation not in ("idle", "sleep"):
            message = (
                companion_care_together(state, body.user_id, companion_day(now_ms))
                or message
            )
            playground = state.setdefault("playground", {})
            playground["last_carer"] = me["name"]
            playground["last_care_action"] = body.action
    elif body.action == "game":
        try:
            message = companion_game_act(
                state, body.user_id, partner["id"], body.value, companion_day(now_ms)
            )
        except (ValueError, KeyError) as exc:
            con.rollback()
            con.close()
            raise HTTPException(409, str(exc))
        animation = "play"
        while state["level"] < 10 and state["xp"] >= companion_required_xp(
            state["level"]
        ):
            state["xp"] -= companion_required_xp(state["level"])
            state["level"] += 1
            state["coins"] += 20
    elif body.action == "buy_food":
        try:
            state = companion_advance(state, now_ms)
            message = companion_buy_food(state, body.value)
        except (ValueError, KeyError) as exc:
            con.rollback()
            con.close()
            raise HTTPException(409, str(exc))
        state["lastAction"] = now_ms
        playground = state.setdefault("playground", {})
        playground["last_carer"] = me["name"]
        playground["last_care_action"] = "feed"
        animation = "feed"
    elif body.action == "room":
        room = body.value
        if room not in COMPANION_ROOMS:
            con.rollback()
            con.close()
            raise HTTPException(400, "room not found")
        owned = set(state["ownedRooms"])
        if room in owned:
            state["room"], message = room, "Комната выбрана"
        elif int(state["coins"]) < COMPANION_ROOMS[room]:
            message = f"Нужно ещё {COMPANION_ROOMS[room] - int(state['coins'])} монет"
        else:
            state["coins"] = int(state["coins"]) - COMPANION_ROOMS[room]
            state["room"] = room
            state["ownedRooms"] = list(owned | {room})
            message = "Комната ваша навсегда ✨"
    elif body.action == "accessory":
        levels = {"none": 1, "bow": 2, "crown": 5}
        if body.value not in levels:
            con.rollback()
            con.close()
            raise HTTPException(400, "accessory not found")
        earned = int(state.get("playground", {}).get("completed", 0))
        game_unlocked = (body.value == "bow" and earned >= 3) or (
            body.value == "crown" and earned >= 10
        )
        if int(state["level"]) < levels[body.value] and not game_unlocked:
            con.rollback()
            con.close()
            raise HTTPException(409, "accessory is locked")
        state["accessory"], message = body.value, "Украшение выбрано"
    elif body.action == "rename":
        name = body.value.strip()
        if not name or len(name) > 24:
            con.rollback()
            con.close()
            raise HTTPException(400, "invalid companion name")
        state["name"], message = name, "Новое имя сохранено"
    elif body.action == "reset":
        state, message = fresh_companion(), "Можно выбрать нового друга вместе"
    else:
        con.rollback()
        con.close()
        raise HTTPException(400, "bad action")
    version = row["version"] + 1
    con.execute(
        "UPDATE companions SET state=?,proposal_type='',proposal_name='',proposed_by=NULL,version=?,updated_at=? WHERE pair_key=?",
        (
            json.dumps(state),
            version,
            utc_iso(),
            pair_key,
        ),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "companion")
    return companion_response(None, state, version, body.user_id, message, animation)


# ---------------- онлайн-игры для пары ----------------
SYNC_ROUNDS = [
    ("Идеальный вечер вдвоём?", ["Кино дома", "Прогулка", "Ресторан", "Приключение"]),
    (
        "Куда сорвёмся на выходные?",
        ["К морю", "В горы", "В новый город", "Останемся дома"],
    ),
    ("Какой сюрприз приятнее?", ["Письмо", "Подарок", "Свидание", "Завтрак в постель"]),
    (
        "Наш общий супернавык?",
        ["Смешить", "Поддерживать", "Путешествовать", "Создавать уют"],
    ),
    ("Что выберем прямо сейчас?", ["Обниматься", "Гулять", "Готовить", "Играть"]),
    (
        "Как выглядит идеальное утро?",
        ["Спать долго", "Кофе в кровать", "Спорт", "Раннее путешествие"],
    ),
]


def game_couple(user_id: int):
    me, partner = couple_of(user_id)
    if not partner:
        return me, None, str(me["id"])
    return me, partner, f"{min(me['id'], partner['id'])}:{max(me['id'], partner['id'])}"


def fresh_game(kind: str, first: int):
    if kind == "tic_tac_toe":
        return {"board": [""] * 9, "turn": first, "winner": None, "draw": False}
    if kind == "sync":
        return {"round": 0, "picks": {}, "score": 0, "revealed": False}
    raise HTTPException(404, "unknown game")


def game_response(kind: str, state: dict, version: int, me, partner):
    base = {
        "kind": kind,
        "waiting": partner is None,
        "partner_name": partner["name"] if partner else None,
        "version": version,
    }
    if partner is None:
        return base
    if kind == "tic_tac_toe":
        return {
            **base,
            "board": state["board"],
            "turn": state.get("turn"),
            "winner": state.get("winner"),
            "draw": bool(state.get("draw", False)),
            "my_symbol": "X" if me["id"] == min(me["id"], partner["id"]) else "O",
            "my_turn": state.get("turn") == me["id"],
            "result": (
                "win"
                if state.get("winner") == me["id"]
                else (
                    "lose"
                    if state.get("winner") == partner["id"]
                    else "draw" if state.get("draw") else "playing"
                )
            ),
        }
    idx = int(state.get("round", 0)) % len(SYNC_ROUNDS)
    prompt, options = SYNC_ROUNDS[idx]
    picks = state.get("picks", {})
    mine, theirs = picks.get(str(me["id"])), picks.get(str(partner["id"]))
    revealed = bool(state.get("revealed", False))
    return {
        **base,
        "round": int(state.get("round", 0)),
        "prompt": prompt,
        "options": options,
        "my_choice": mine,
        "partner_chosen": theirs is not None,
        "partner_choice": theirs if revealed else None,
        "score": int(state.get("score", 0)),
        "revealed": revealed,
    }


@protected.get("/games/{kind}")
def game_get(kind: str, user_id: int):
    me, partner, pair_key = game_couple(user_id)
    if not partner:
        return game_response(kind, fresh_game(kind, me["id"]), 0, me, partner)
    con = db()
    row = con.execute(
        "SELECT state,version FROM couple_games WHERE pair_key=? AND kind=?",
        (pair_key, kind),
    ).fetchone()
    if row:
        state, version = json.loads(row["state"]), row["version"]
    else:
        state, version = fresh_game(kind, min(me["id"], partner["id"])), 1
        con.execute(
            "INSERT INTO couple_games(pair_key,kind,state,version,updated_at) VALUES(?,?,?,?,?)",
            (
                pair_key,
                kind,
                json.dumps(state),
                version,
                utc_iso(),
            ),
        )
        con.commit()
    con.close()
    return game_response(kind, state, version, me, partner)


@protected.post("/games/{kind}/action")
async def game_action(kind: str, body: GameActionIn):
    me, partner, pair_key = game_couple(body.user_id)
    if not partner:
        raise HTTPException(400, "partner has not joined yet")
    con = db()
    con.execute("BEGIN IMMEDIATE")

    def reject(status: int, message: str):
        con.rollback()
        con.close()
        raise HTTPException(status, message)

    row = con.execute(
        "SELECT state,version FROM couple_games WHERE pair_key=? AND kind=?",
        (pair_key, kind),
    ).fetchone()
    state = (
        json.loads(row["state"])
        if row
        else fresh_game(kind, min(me["id"], partner["id"]))
    )
    version = row["version"] if row else 0
    if kind == "tic_tac_toe":
        if body.action == "reset":
            state = fresh_game(kind, min(me["id"], partner["id"]))
        elif body.action == "move":
            cell = body.value
            if cell is None or cell not in range(9):
                reject(400, "bad cell")
            if state.get("winner") is not None or state.get("draw"):
                reject(409, "game finished")
            if state.get("turn") != me["id"]:
                reject(409, "not your turn")
            if state["board"][cell]:
                reject(409, "cell occupied")
            symbol = "X" if me["id"] == min(me["id"], partner["id"]) else "O"
            state["board"][cell] = symbol
            wins = (
                (0, 1, 2),
                (3, 4, 5),
                (6, 7, 8),
                (0, 3, 6),
                (1, 4, 7),
                (2, 5, 8),
                (0, 4, 8),
                (2, 4, 6),
            )
            if any(all(state["board"][i] == symbol for i in line) for line in wins):
                state["winner"], state["turn"] = me["id"], None
            elif all(state["board"]):
                state["draw"], state["turn"] = True, None
            else:
                state["turn"] = partner["id"]
        else:
            reject(400, "bad action")
    elif kind == "sync":
        if body.action == "choose":
            value = body.value
            if value is None or value not in range(
                len(SYNC_ROUNDS[int(state.get("round", 0)) % len(SYNC_ROUNDS)][1])
            ):
                reject(400, "bad choice")
            if state.get("revealed"):
                reject(409, "round finished")
            picks = state.setdefault("picks", {})
            if str(me["id"]) in picks:
                reject(409, "already chosen")
            picks[str(me["id"])] = value
            if str(partner["id"]) in picks:
                state["revealed"] = True
                if picks[str(me["id"])] == picks[str(partner["id"])]:
                    state["score"] = int(state.get("score", 0)) + 1
        elif body.action == "next":
            if not state.get("revealed"):
                reject(409, "wait for both answers")
            state = {
                "round": int(state.get("round", 0)) + 1,
                "picks": {},
                "score": int(state.get("score", 0)),
                "revealed": False,
            }
        elif body.action == "reset":
            state = fresh_game(kind, min(me["id"], partner["id"]))
        else:
            reject(400, "bad action")
    else:
        reject(404, "unknown game")
    version += 1
    con.execute(
        "INSERT OR REPLACE INTO couple_games(pair_key,kind,state,version,updated_at) VALUES(?,?,?,?,?)",
        (
            pair_key,
            kind,
            json.dumps(state),
            version,
            utc_iso(),
        ),
    )
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "game")
    return game_response(kind, state, version, me, partner)


# ---------------- публичная карта пар ----------------
def community_map_name(value: str) -> str:
    return " ".join((value or "").split())[:40]


def community_map_post_object(row, user_id: int):
    country = COUNTRIES_BY_CODE.get(row["country_code"] or "")
    mine = user_id in (row["pair_low_id"], row["pair_high_id"])
    published = bool(row["low_approved"] and row["high_approved"] and not row["hidden"])
    my_approved = (
        row["low_approved"] if user_id == row["pair_low_id"] else row["high_approved"]
    )
    lat = float(row["lat"])
    lon = float(row["lon"])
    return {
        "id": row["id"],
        "country_code": row["country_code"] or "",
        "country_name_ru": country["name_ru"] if country else "",
        "country_name_en": country["name_en"] if country else "",
        "lat": lat,
        "lon": lon,
        "photo": row["photo"],
        "comment": row["comment"],
        "couple_name": " & ".join(
            (community_map_name(row["low_name"]), community_map_name(row["high_name"]))
        ),
        "updated_at": row["updated_at"],
        "mine": mine,
        "published": published,
        "can_approve": bool(mine and not published and not my_approved),
        "likes_count": int(row["likes_count"]),
        "liked_by_me": bool(row["liked_by_me"]),
        "comments_count": int(row["comments_count"]),
    }


def community_map_post_row(con, post_id: int, user_id: int):
    return con.execute(
        "SELECT p.*,low.name AS low_name,high.name AS high_name,"
        "(SELECT COUNT(*) FROM community_map_likes l WHERE l.post_id=p.id) "
        "AS likes_count,"
        "EXISTS(SELECT 1 FROM community_map_likes l "
        "WHERE l.post_id=p.id AND l.user_id=?) AS liked_by_me,"
        "(SELECT COUNT(*) FROM community_map_comments c "
        "WHERE c.post_id=p.id AND c.hidden=0) AS comments_count "
        "FROM community_map_posts p "
        "JOIN users low ON low.id=p.pair_low_id "
        "JOIN users high ON high.id=p.pair_high_id "
        "WHERE p.id=? AND low.partner_id=high.id AND high.partner_id=low.id",
        (user_id, post_id),
    ).fetchone()


def community_map_public_post_row(con, post_id: int):
    return con.execute(
        "SELECT p.* FROM community_map_posts p "
        "JOIN users low ON low.id=p.pair_low_id "
        "JOIN users high ON high.id=p.pair_high_id "
        "WHERE p.id=? AND p.hidden=0 AND p.low_approved=1 AND p.high_approved=1 "
        "AND low.partner_id=high.id AND high.partner_id=low.id",
        (post_id,),
    ).fetchone()


def community_map_comment_object(row, user_id: int, post_owner: bool = False):
    mine = row["author_user_id"] == user_id
    return {
        "id": row["id"],
        "text": row["text"],
        "author_name": community_map_name(row["author_name"]),
        "created_at": row["created_at"],
        "mine": mine,
        "can_delete": bool(mine or post_owner),
        "can_report": bool(not mine and not post_owner),
    }


def community_map_delete_interactions(con, post_id: int):
    con.execute(
        "DELETE FROM community_map_comment_reports WHERE comment_id IN "
        "(SELECT id FROM community_map_comments WHERE post_id=?)",
        (post_id,),
    )
    con.execute("DELETE FROM community_map_comments WHERE post_id=?", (post_id,))
    con.execute("DELETE FROM community_map_likes WHERE post_id=?", (post_id,))
    con.execute("DELETE FROM community_map_reports WHERE post_id=?", (post_id,))


@protected.get("/community/map/countries")
def community_map_countries(user_id: int):
    couple_of(user_id)
    return COUNTRY_CATALOG


@protected.get("/community/map")
def community_map_list(user_id: int):
    couple_of(user_id)
    con = db()
    try:
        rows = con.execute(
            "SELECT p.*,low.name AS low_name,high.name AS high_name,"
            "(SELECT COUNT(*) FROM community_map_likes l WHERE l.post_id=p.id) "
            "AS likes_count,"
            "EXISTS(SELECT 1 FROM community_map_likes l "
            "WHERE l.post_id=p.id AND l.user_id=?) AS liked_by_me,"
            "(SELECT COUNT(*) FROM community_map_comments c "
            "WHERE c.post_id=p.id AND c.hidden=0) AS comments_count "
            "FROM community_map_posts p "
            "JOIN users low ON low.id=p.pair_low_id "
            "JOIN users high ON high.id=p.pair_high_id "
            "WHERE low.partner_id=high.id AND high.partner_id=low.id AND p.hidden=0 AND "
            "((p.low_approved=1 AND p.high_approved=1) OR "
            "((p.pair_low_id=? OR p.pair_high_id=?) AND "
            "(p.low_approved=0 OR p.high_approved=0))) "
            "ORDER BY p.updated_at DESC,p.id DESC",
            (user_id, user_id, user_id),
        ).fetchall()
        return [community_map_post_object(row, user_id) for row in rows]
    finally:
        con.close()


@protected.post("/community/map")
def community_map_upsert(body: CommunityMapPostIn):
    me, partner, low, high = movie_couple(body.user_id)
    lat = float(body.lat)
    lon = float(body.lon)
    if (
        not math.isfinite(lat)
        or not math.isfinite(lon)
        or lat < -90
        or lat > 90
        or lon < -180
        or lon > 180
    ):
        raise HTTPException(400, "coordinates out of range")
    country_code = body.country_code.strip().upper() if body.country_code else ""
    if country_code and country_code not in COUNTRIES_BY_CODE:
        raise HTTPException(400, "unknown country code")
    photo_name = managed_photo_name(body.photo)
    if not photo_name or body.photo != f"/photos/{photo_name}":
        raise HTTPException(400, "photo must be a managed /photos URL")
    comment = body.comment.strip()
    if not 1 <= len(comment) <= 500:
        raise HTTPException(400, "comment must contain 1 to 500 characters")
    if any(unicodedata.category(char) == "Cc" for char in comment):
        raise HTTPException(400, "comment contains control characters")
    if not body.public_consent:
        raise HTTPException(400, "public consent is required")
    now = utc_iso()
    low_approved = 1 if me["id"] == low else 0
    high_approved = 1 if me["id"] == high else 0
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        owner = con.execute(
            "SELECT 1 FROM photo_owners WHERE name=? AND user_id IN (?,?)",
            (photo_name, me["id"], partner["id"]),
        ).fetchone()
        if not owner:
            raise HTTPException(403, "photo is not owned by this couple")
        existing = con.execute(
            "SELECT id FROM community_map_posts WHERE pair_low_id=? "
            "AND pair_high_id=? AND lat=? AND lon=?",
            (low, high, lat, lon),
        ).fetchone()
        if not existing:
            count = con.execute(
                "SELECT COUNT(*) n FROM community_map_posts "
                "WHERE pair_low_id=? AND pair_high_id=?",
                (low, high),
            ).fetchone()["n"]
            if count >= 30:
                raise HTTPException(409, "a couple can publish at most 30 points")
            post_id = con.execute(
                "INSERT INTO community_map_posts(pair_low_id,pair_high_id,"
                "created_by_user_id,country_code,lat,lon,photo,comment,low_approved,"
                "high_approved,hidden,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,0,?,?)",
                (
                    low,
                    high,
                    me["id"],
                    country_code,
                    lat,
                    lon,
                    body.photo,
                    comment,
                    low_approved,
                    high_approved,
                    now,
                    now,
                ),
            ).lastrowid
        else:
            post_id = existing["id"]
            con.execute(
                "UPDATE community_map_posts SET created_by_user_id=?,country_code=?,lat=?,lon=?,photo=?,comment=?,"
                "low_approved=?,high_approved=?,hidden=0,updated_at=? WHERE id=?",
                (
                    me["id"],
                    country_code,
                    lat,
                    lon,
                    body.photo,
                    comment,
                    low_approved,
                    high_approved,
                    now,
                    post_id,
                ),
            )
            community_map_delete_interactions(con, post_id)
        row = community_map_post_row(con, post_id, body.user_id)
        con.commit()
        return community_map_post_object(row, body.user_id)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.post("/community/map/{post_id}/approve")
def community_map_approve(post_id: int, body: CommunityMapUserIn):
    me, partner, low, high = movie_couple(body.user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = community_map_post_row(con, post_id, body.user_id)
        if not row or (row["pair_low_id"], row["pair_high_id"]) != (low, high):
            raise HTTPException(404, "map post not found")
        now = utc_iso()
        if me["id"] == low:
            con.execute(
                "UPDATE community_map_posts SET low_approved=1,updated_at=? WHERE id=?",
                (now, post_id),
            )
        else:
            con.execute(
                "UPDATE community_map_posts SET high_approved=1,updated_at=? WHERE id=?",
                (now, post_id),
            )
        row = community_map_post_row(con, post_id, body.user_id)
        con.commit()
        return community_map_post_object(row, body.user_id)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.delete("/community/map/{post_id}")
def community_map_delete(post_id: int, user_id: int):
    couple_of(user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT pair_low_id,pair_high_id FROM community_map_posts WHERE id=?",
            (post_id,),
        ).fetchone()
        if not row or user_id not in (row["pair_low_id"], row["pair_high_id"]):
            raise HTTPException(404, "map post not found")
        community_map_delete_interactions(con, post_id)
        con.execute("DELETE FROM community_map_posts WHERE id=?", (post_id,))
        con.commit()
        return {"ok": True}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.post("/community/map/{post_id}/report")
def community_map_report(post_id: int, body: CommunityMapReportIn):
    couple_of(body.user_id)
    if body.reason not in {"privacy", "spam", "inappropriate", "other"}:
        raise HTTPException(400, "invalid report reason")
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = community_map_public_post_row(con, post_id)
        if not row or body.user_id in (row["pair_low_id"], row["pair_high_id"]):
            raise HTTPException(404, "published map post not found")
        now = utc_iso()
        con.execute(
            "INSERT OR IGNORE INTO community_map_reports("
            "post_id,reporter_user_id,reason,created_at) VALUES(?,?,?,?)",
            (post_id, body.user_id, body.reason, now),
        )
        reports = con.execute(
            "SELECT COUNT(*) n FROM community_map_reports WHERE post_id=?",
            (post_id,),
        ).fetchone()["n"]
        if reports >= 3:
            con.execute(
                "UPDATE community_map_posts SET hidden=1 WHERE id=?", (post_id,)
            )
        con.commit()
        return {"ok": True}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.post("/community/map/{post_id}/like")
def community_map_like(post_id: int, body: CommunityMapLikeIn):
    couple_of(body.user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        post = community_map_public_post_row(con, post_id)
        if not post or body.user_id in (post["pair_low_id"], post["pair_high_id"]):
            raise HTTPException(404, "published map post not found")
        if body.liked:
            con.execute(
                "INSERT OR IGNORE INTO community_map_likes(post_id,user_id,created_at) "
                "VALUES(?,?,?)",
                (
                    post_id,
                    body.user_id,
                    utc_iso(),
                ),
            )
        else:
            con.execute(
                "DELETE FROM community_map_likes WHERE post_id=? AND user_id=?",
                (post_id, body.user_id),
            )
        likes_count = con.execute(
            "SELECT COUNT(*) n FROM community_map_likes WHERE post_id=?", (post_id,)
        ).fetchone()["n"]
        con.commit()
        return {
            "post_id": post_id,
            "liked_by_me": body.liked,
            "likes_count": likes_count,
        }
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.get("/community/map/{post_id}/comments")
def community_map_comments(post_id: int, user_id: int):
    couple_of(user_id)
    con = db()
    try:
        post = community_map_public_post_row(con, post_id)
        if not post:
            raise HTTPException(404, "published map post not found")
        post_owner = user_id in (post["pair_low_id"], post["pair_high_id"])
        rows = con.execute(
            "SELECT c.*,u.name AS author_name FROM community_map_comments c "
            "JOIN users u ON u.id=c.author_user_id "
            "WHERE c.post_id=? AND c.hidden=0 ORDER BY c.id ASC LIMIT 100",
            (post_id,),
        ).fetchall()
        return [community_map_comment_object(row, user_id, post_owner) for row in rows]
    finally:
        con.close()


@protected.post("/community/map/{post_id}/comments")
def community_map_comment_add(post_id: int, body: CommunityMapCommentIn):
    couple_of(body.user_id)
    text = body.text.strip()
    if not 1 <= len(text) <= 300:
        raise HTTPException(400, "comment must contain 1 to 300 characters")
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise HTTPException(400, "comment contains control characters")
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        post = community_map_public_post_row(con, post_id)
        if not post or body.user_id in (post["pair_low_id"], post["pair_high_id"]):
            raise HTTPException(404, "published map post not found")
        count = con.execute(
            "SELECT COUNT(*) n FROM community_map_comments "
            "WHERE post_id=? AND author_user_id=? AND hidden=0",
            (post_id, body.user_id),
        ).fetchone()["n"]
        if count >= 20:
            raise HTTPException(409, "comment limit reached")
        now = utc_iso()
        comment_id = con.execute(
            "INSERT INTO community_map_comments(post_id,author_user_id,text,created_at) "
            "VALUES(?,?,?,?)",
            (post_id, body.user_id, text, now),
        ).lastrowid
        row = con.execute(
            "SELECT c.*,u.name AS author_name FROM community_map_comments c "
            "JOIN users u ON u.id=c.author_user_id WHERE c.id=?",
            (comment_id,),
        ).fetchone()
        con.commit()
        return community_map_comment_object(row, body.user_id)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.delete("/community/map/{post_id}/comments/{comment_id}")
def community_map_comment_delete(post_id: int, comment_id: int, user_id: int):
    couple_of(user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        post = community_map_public_post_row(con, post_id)
        comment = con.execute(
            "SELECT author_user_id FROM community_map_comments "
            "WHERE id=? AND post_id=?",
            (comment_id, post_id),
        ).fetchone()
        if (
            not post
            or not comment
            or user_id
            not in (
                comment["author_user_id"],
                post["pair_low_id"],
                post["pair_high_id"],
            )
        ):
            raise HTTPException(404, "comment not found")
        con.execute(
            "DELETE FROM community_map_comment_reports WHERE comment_id=?",
            (comment_id,),
        )
        con.execute("DELETE FROM community_map_comments WHERE id=?", (comment_id,))
        con.commit()
        return {"ok": True}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.post("/community/map/{post_id}/comments/{comment_id}/report")
def community_map_comment_report(
    post_id: int, comment_id: int, body: CommunityMapCommentReportIn
):
    couple_of(body.user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        post = community_map_public_post_row(con, post_id)
        comment = con.execute(
            "SELECT author_user_id FROM community_map_comments "
            "WHERE id=? AND post_id=? AND hidden=0",
            (comment_id, post_id),
        ).fetchone()
        if (
            not post
            or not comment
            or comment["author_user_id"] == body.user_id
            or body.user_id in (post["pair_low_id"], post["pair_high_id"])
        ):
            raise HTTPException(404, "comment not found")
        now = utc_iso()
        con.execute(
            "INSERT OR IGNORE INTO community_map_comment_reports("
            "comment_id,reporter_user_id,reason,created_at) VALUES(?,?,?,?)",
            (comment_id, body.user_id, body.reason, now),
        )
        reports = con.execute(
            "SELECT COUNT(*) n FROM community_map_comment_reports WHERE comment_id=?",
            (comment_id,),
        ).fetchone()["n"]
        if reports >= 3:
            con.execute(
                "UPDATE community_map_comments SET hidden=1 WHERE id=?", (comment_id,)
            )
        con.commit()
        return {"ok": True}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ---------------- фильмы для пары ----------------
def movie_couple(user_id: int):
    me, partner = couple_of(user_id)
    if not partner or partner["partner_id"] != me["id"]:
        raise HTTPException(409, "Сначала подключитесь друг к другу как партнёры")
    low, high = sorted((me["id"], partner["id"]))
    return me, partner, low, high


def movie_object(row):
    if not row:
        return None
    return dict(row)


def insert_movie_match(con, low: int, high: int, genre_key, movie, matched_at):
    con.execute(
        "INSERT OR IGNORE INTO movie_matches("
        "pair_low_id,pair_high_id,movie_id,genre_key,title,title_en,overview,"
        "overview_en,release_year,poster_url,genres,runtime_min,rating,"
        "rating_source,watched,watched_at,matched_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,'',?)",
        (
            low,
            high,
            movie["id"],
            genre_key or "",
            movie.get("title", ""),
            movie.get("title_en", ""),
            movie.get("overview", ""),
            movie.get("overview_en", ""),
            movie.get("release_year"),
            movie.get("poster_url", ""),
            ",".join(movie.get("genres") or []),
            movie.get("runtime_min"),
            movie.get("rating"),
            movie.get("rating_source", ""),
            matched_at,
        ),
    )


def movie_match_object(row):
    return {
        "movie": {
            "id": row["movie_id"],
            "title": row["title"],
            "title_en": row["title_en"],
            "overview": row["overview"],
            "overview_en": row["overview_en"],
            "release_year": row["release_year"],
            "poster_url": row["poster_url"],
            "genres": [g for g in (row["genres"] or "").split(",") if g],
            "runtime_min": row["runtime_min"],
            "rating": row["rating"],
            "rating_source": row["rating_source"],
        },
        "watched": bool(row["watched"]),
        "matched_at": row["matched_at"],
    }


def backfill_movie_matches(con):
    pending = con.execute(
        "SELECT r.pair_low_id AS pair_low_id, r.pair_high_id AS pair_high_id, "
        "r.matched_movie_id AS movie_id, r.genre_key AS genre_key, "
        "r.created_at AS matched_at FROM movie_rounds r "
        "LEFT JOIN movie_matches m ON m.pair_low_id=r.pair_low_id "
        "AND m.pair_high_id=r.pair_high_id AND m.movie_id=r.matched_movie_id "
        "WHERE r.status='matched' AND r.matched_movie_id IS NOT NULL "
        "AND m.id IS NULL"
    ).fetchall()
    if not pending:
        return
    catalogs = {}
    for row in pending:
        genre_key = row["genre_key"] or "all"
        if genre_key not in catalogs:
            try:
                catalogs[genre_key] = list(movie_provider.catalog(genre_key))
            except MovieProviderError:
                catalogs[genre_key] = []
        movie = next(
            (item for item in catalogs[genre_key] if item["id"] == row["movie_id"]),
            None,
        )
        if movie:
            insert_movie_match(
                con,
                row["pair_low_id"],
                row["pair_high_id"],
                genre_key,
                movie,
                row["matched_at"],
            )


def movie_latest_round(con, low: int, high: int, create: bool = True):
    row = con.execute(
        "SELECT * FROM movie_rounds WHERE pair_low_id=? AND pair_high_id=? "
        "ORDER BY id DESC LIMIT 1",
        (low, high),
    ).fetchone()
    if not row and create:
        now = utc_iso()
        round_id = con.execute(
            "INSERT INTO movie_rounds(pair_low_id,pair_high_id,status,created_at) "
            "VALUES(?,?,'active',?)",
            (low, high, now),
        ).lastrowid
        row = con.execute(
            "SELECT * FROM movie_rounds WHERE id=?", (round_id,)
        ).fetchone()
    return row


def movie_rows_for_genre(con, genre_key: str, round_id: int):
    try:
        rows = list(movie_provider.catalog(genre_key))
    except MovieProviderError as error:
        raise HTTPException(503, str(error)) from error
    random.Random(f"{genre_key}:{round_id}").shuffle(rows)
    return rows


def movie_genre_options(con):
    return movie_provider.genre_options()


def movie_next(rows, con, round_id: int, user_id: int):
    swiped = {
        row["movie_id"]
        for row in con.execute(
            "SELECT movie_id FROM movie_swipes WHERE round_id=? AND user_id=?",
            (round_id, user_id),
        ).fetchall()
    }
    return next((row for row in rows if row["id"] not in swiped), None)


def movie_state(con, round_row, me, partner):
    genre_key = round_row["genre_key"]
    rows = movie_rows_for_genre(con, genre_key, round_row["id"]) if genre_key else []
    total = len(rows)
    counts = {}
    for uid in (me["id"], partner["id"]):
        counts[uid] = con.execute(
            "SELECT COUNT(*) n FROM movie_swipes WHERE round_id=? AND user_id=?",
            (round_row["id"], uid),
        ).fetchone()["n"]
    status = round_row["status"]
    if (
        genre_key
        and status == "active"
        and all(movie_next(rows, con, round_row["id"], uid) is None for uid in counts)
    ):
        con.execute(
            "UPDATE movie_rounds SET status='exhausted' WHERE id=?", (round_row["id"],)
        )
        status = "exhausted"
    movie = None
    if status == "active" and genre_key:
        movie = movie_next(rows, con, round_row["id"], me["id"])
    match = None
    matched_movie_id = round_row["matched_movie_id"]
    if status == "matched" and matched_movie_id:
        match = next((item for item in rows if item["id"] == matched_movie_id), None)
    return {
        "round_id": round_row["id"],
        "status": status,
        "swiped_count": counts[me["id"]],
        "catalog_total": total,
        "partner_name": partner["name"],
        "movie": movie_object(movie),
        "match": movie_object(match),
        "genre_key": genre_key,
        "needs_genre": status == "active" and not genre_key,
        "available_genres": movie_genre_options(con),
    }


@protected.get("/movies/state")
def movies_state(user_id: int):
    me, partner, low, high = movie_couple(user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        round_row = movie_latest_round(con, low, high)
        result = movie_state(con, round_row, me, partner)
        con.commit()
        return result
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@protected.post("/movies/swipe")
async def movies_swipe(body: MovieSwipeIn):
    me, partner, low, high = movie_couple(body.user_id)
    decision = {"left": "heart", "right": "skip"}.get(body.direction)
    if not decision:
        raise HTTPException(400, "direction must be left or right")
    con = db()
    changed = False
    try:
        con.execute("BEGIN IMMEDIATE")
        round_row = movie_latest_round(con, low, high)
        existing = con.execute(
            "SELECT decision FROM movie_swipes WHERE round_id=? AND user_id=? AND movie_id=?",
            (round_row["id"], me["id"], body.movie_id),
        ).fetchone()
        if existing:
            if existing["decision"] != decision:
                raise HTTPException(
                    409, "movie already swiped in the opposite direction"
                )
            result = movie_state(con, round_row, me, partner)
            con.commit()
            return result
        if round_row["status"] != "active":
            raise HTTPException(409, "round is finished; reset to start a new round")
        genre_key = round_row["genre_key"]
        if not genre_key:
            raise HTTPException(409, "Сначала выберите жанр фильма")
        current = movie_next(
            movie_rows_for_genre(con, genre_key, round_row["id"]),
            con,
            round_row["id"],
            me["id"],
        )
        if not current or current["id"] != body.movie_id:
            raise HTTPException(409, "movie is not the current catalog item")
        now = utc_iso()
        con.execute(
            "INSERT INTO movie_swipes(round_id,user_id,movie_id,decision,created_at) "
            "VALUES(?,?,?,?,?)",
            (round_row["id"], me["id"], body.movie_id, decision, now),
        )
        changed = True
        if (
            decision == "heart"
            and con.execute(
                "SELECT 1 FROM movie_swipes WHERE round_id=? AND user_id=? "
                "AND movie_id=? AND decision='heart'",
                (round_row["id"], partner["id"], body.movie_id),
            ).fetchone()
        ):
            con.execute(
                "UPDATE movie_rounds SET status='matched',matched_movie_id=? "
                "WHERE id=? AND status='active'",
                (body.movie_id, round_row["id"]),
            )
            insert_movie_match(con, low, high, genre_key, current, now)
        round_row = con.execute(
            "SELECT * FROM movie_rounds WHERE id=?", (round_row["id"],)
        ).fetchone()
        result = movie_state(con, round_row, me, partner)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    if changed:
        await wsman.ping_couple(body.user_id, "movies")
    return result


@protected.post("/movies/genre")
async def movies_genre(body: MovieGenreIn):
    me, partner, low, high = movie_couple(body.user_id)
    genre_key = body.genre_key.strip().lower()
    if genre_key not in MOVIE_GENRES:
        raise HTTPException(400, "Неизвестный жанр фильма")
    con = db()
    changed = False
    try:
        con.execute("BEGIN IMMEDIATE")
        round_row = movie_latest_round(con, low, high)
        if round_row["status"] != "active":
            raise HTTPException(409, "Начните новый раунд, чтобы выбрать жанр")
        selected = round_row["genre_key"]
        if selected and selected != genre_key:
            raise HTTPException(409, "Жанр этого раунда уже выбран")
        if not selected:
            has_swipes = con.execute(
                "SELECT 1 FROM movie_swipes WHERE round_id=? LIMIT 1",
                (round_row["id"],),
            ).fetchone()
            if has_swipes:
                raise HTTPException(409, "Нельзя изменить жанр после начала свайпов")
            con.execute(
                "UPDATE movie_rounds SET genre_key=? WHERE id=?",
                (genre_key, round_row["id"]),
            )
            changed = True
            round_row = con.execute(
                "SELECT * FROM movie_rounds WHERE id=?", (round_row["id"],)
            ).fetchone()
        result = movie_state(con, round_row, me, partner)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    if changed:
        await wsman.ping_couple(body.user_id, "movies")
    return result


@protected.post("/movies/reset")
async def movies_reset(body: MovieUserIn):
    me, partner, low, high = movie_couple(body.user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE movie_rounds SET status='exhausted' WHERE pair_low_id=? "
            "AND pair_high_id=? AND status='active'",
            (low, high),
        )
        now = utc_iso()
        round_id = con.execute(
            "INSERT INTO movie_rounds(pair_low_id,pair_high_id,status,created_at) "
            "VALUES(?,?,'active',?)",
            (low, high, now),
        ).lastrowid
        round_row = con.execute(
            "SELECT * FROM movie_rounds WHERE id=?", (round_id,)
        ).fetchone()
        result = movie_state(con, round_row, me, partner)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    await wsman.ping_couple(body.user_id, "movies")
    return result


@protected.get("/movies/matches")
def movies_matches(user_id: int):
    me, partner, low, high = movie_couple(user_id)
    con = db()
    try:
        rows = con.execute(
            "SELECT * FROM movie_matches WHERE pair_low_id=? AND pair_high_id=? "
            "AND deleted=0 "
            "ORDER BY watched ASC, matched_at DESC, id DESC",
            (low, high),
        ).fetchall()
    finally:
        con.close()
    return {
        "partner_name": partner["name"],
        "items": [movie_match_object(row) for row in rows],
    }


@protected.post("/movies/matches/watched")
async def movies_matches_watched(body: MovieWatchIn):
    me, partner, low, high = movie_couple(body.user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT id FROM movie_matches WHERE pair_low_id=? AND pair_high_id=? "
            "AND movie_id=? AND deleted=0",
            (low, high, body.movie_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Фильм не найден в списке совпадений")
        watched_at = (
            utc_iso()
            if body.watched
            else ""
        )
        con.execute(
            "UPDATE movie_matches SET watched=?,watched_at=? WHERE id=?",
            (1 if body.watched else 0, watched_at, row["id"]),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    await wsman.ping_couple(body.user_id, "movies")
    return movies_matches(body.user_id)


@protected.delete("/movies/matches/{movie_id}")
async def movies_matches_delete(movie_id: int, user_id: int):
    me, partner, low, high = movie_couple(user_id)
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT id FROM movie_matches WHERE pair_low_id=? AND pair_high_id=? "
            "AND movie_id=? AND deleted=0",
            (low, high, movie_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Фильм не найден в списке совпадений")
        con.execute("UPDATE movie_matches SET deleted=1 WHERE id=?", (row["id"],))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    await wsman.ping_couple(user_id, "movies")
    return movies_matches(user_id)


@app.get("/movies/poster/{filename}", include_in_schema=False)
def movie_poster(filename: str):
    if not filename or any(
        char not in string.ascii_letters + string.digits + "._-" for char in filename
    ):
        raise HTTPException(400, "Некорректное имя постера")
    request = UrlRequest(
        f"https://image.tmdb.org/t/p/w780/{filename}",
        headers={"User-Agent": "Enrwine/1.0"},
    )
    try:
        with urlopen(request, timeout=12) as upstream:
            content = upstream.read()
            media_type = upstream.headers.get_content_type()
    except (HTTPError, URLError, OSError) as error:
        raise HTTPException(502, "Не удалось загрузить постер") from error
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# Keep this mount last so API, WebSocket, photos and APK routes take priority.
app.include_router(protected)
audit_http_routes()
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="flutter_web")
