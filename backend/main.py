"""Enrwine: Python-бэкенд (FastAPI + SQLite).

Запуск:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
Документация: http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from typing import Optional, List
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
import hashlib
import base64
import sqlite3
import datetime
import json
import math
import os
import random
import string

DB = os.environ.get("COUPLE_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "couple.db"))
PHOTO_DIR = os.environ.get("PHOTO_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos"))

app = FastAPI(title="Enrwine API", version="1.0")

# Токен текущего HTTP-запроса (заголовок X-Auth-Token). WebSocket идёт мимо
# middleware — там токен передаётся явным query-параметром.
_request_token: ContextVar[str] = ContextVar("request_token", default="")


class AuthTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        _request_token.set(request.headers.get("x-auth-token", ""))
        return await call_next(request)


app.add_middleware(AuthTokenMiddleware)


def new_token() -> str:
    return secrets.token_hex(16)

# ---------------- seed-данные ----------------
QUESTIONS = [
    "Какое ваше самое тёплое общее воспоминание?",
    "Идеальное свидание мечты — опишите его.",
    "Чему вы научились друг у друга за последнее время?",
    "Какой маленький жест партнёра радует вас больше всего?",
    "Куда бы вы хотели поехать вместе в первую очередь?",
    "Какая песня ассоциируется у вас с вашими отношениями?",
    "О чём вы мечтаете через 5 лет — вместе?",
    "Какой поступок партнёра вас недавно тронул?",
    "Что бы вы хотели чаще делать вместе?",
    "За что вы благодарны партнёру сегодня?",
    "Ваше любимое домашнее занятие вдвоём?",
    "Какой сюрприз вы бы хотели устроить партнёру?",
    "Что для вас значит «дом»?",
    "Какая традиция могла бы стать вашей общей?",
]

QUIZZES = [
    {"title": "Насколько вы совпадаете?",
     "questions": [
         {"text": "Идеальный вечер пятницы?",
          "options": ["Кино дома", "Прогулка", "Ресторан", "Вечеринка с друзьями"]},
         {"text": "Кто готовит завтрак?",
          "options": ["Я", "Партнёр", "Вместе", "Заказываем"]},
         {"text": "Отпуск мечты?",
          "options": ["Море", "Горы", "Город", "Деревня"]},
         {"text": "Фильм на вечер выбирает…",
          "options": ["Я", "Партнёр", "По очереди", "Случайно"]},
         {"text": "Утро выходного дня?",
          "options": ["Спим долго", "Ранний подъём", "Спорт", "Бранч"]},
     ]},
    {"title": "Это или то? ⚡",
     "questions": [
         {"text": "Море или горы?", "options": ["Море", "Горы"]},
         {"text": "Кошки или собаки?", "options": ["Кошки", "Собаки"]},
         {"text": "Ты жаворонок или сова?", "options": ["Жаворонок", "Сова"]},
         {"text": "Чай или кофе?", "options": ["Чай", "Кофе"]},
         {"text": "Кино дома или кинотеатр?", "options": ["Дома", "Кинотеатр"]},
         {"text": "На отдыхе: пляж или экскурсии?", "options": ["Пляж", "Экскурсии"]},
         {"text": "Сладкое или солёное?", "options": ["Сладкое", "Солёное"]},
         {"text": "Лето или зима?", "options": ["Лето", "Зима"]},
      ]},
    {"title": "Язык любви 💗",
     "questions": [
         {"text": "Что сильнее всего помогает почувствовать любовь?", "options": ["Тёплые слова", "Время вдвоём", "Помощь и забота", "Прикосновения"]},
         {"text": "Какой сюрприз приятнее?", "options": ["Любовное сообщение", "Спонтанное свидание", "Полезная помощь", "Небольшой подарок"]},
         {"text": "После тяжёлого дня хочется…", "options": ["Поговорить", "Обняться", "Побыть рядом молча", "Чтобы обо мне позаботились"]},
         {"text": "Что важнее слышать от партнёра?", "options": ["Я тебя люблю", "Я тобой горжусь", "Я рядом", "Я помогу"]},
         {"text": "Идеальный знак внимания?", "options": ["Комплимент", "Совместный вечер", "Завтрак в постель", "Неожиданный подарок"]},
         {"text": "Как лучше мириться?", "options": ["Всё обсудить", "Сначала обняться", "Дать немного времени", "Сделать добрый жест"]},
     ]},
    {"title": "Быт и привычки 🏠",
     "questions": [
         {"text": "Порядок дома — это…", "options": ["Всегда идеально", "Уютный порядок", "Убираемся по выходным", "Главное — не искать вещи"]},
         {"text": "Кто планирует покупки?", "options": ["Я", "Партнёр", "Вместе", "Покупаем спонтанно"]},
         {"text": "Ужин в будний день?", "options": ["Готовим вместе", "Готовит кто свободен", "Доставка", "Каждый выбирает своё"]},
         {"text": "Как проводить свободный вечер дома?", "options": ["Сериал", "Игры", "Разговоры", "Каждый своим делом"]},
         {"text": "Когда лучше решать бытовые вопросы?", "options": ["Сразу", "По плану", "На выходных", "Когда станет срочно"]},
         {"text": "Общий бюджет удобнее вести…", "options": ["Полностью вместе", "Частично вместе", "Раздельно", "Без строгого учёта"]},
     ]},
    {"title": "Отдых и приключения 🌍",
     "questions": [
         {"text": "Идеальная поездка?", "options": ["Море", "Горы", "Новый город", "Домик на природе"]},
         {"text": "Путешествие лучше…", "options": ["Планировать заранее", "Оставить место сюрпризам", "Купить готовый тур", "Решить в последний момент"]},
         {"text": "Темп отпуска?", "options": ["Много впечатлений", "Баланс", "Полный релакс", "Как получится"]},
         {"text": "Лучшее свидание вне дома?", "options": ["Ресторан", "Прогулка", "Концерт", "Активное приключение"]},
         {"text": "Что фотографировать в поездке?", "options": ["Нас двоих", "Красивые места", "Еду и детали", "Лучше проживать момент"]},
         {"text": "Куда поехать без подготовки?", "options": ["За город", "В соседний город", "На фестиваль", "К воде"]},
     ]},
    {"title": "Как мы общаемся 💬",
     "questions": [
         {"text": "Если что-то тревожит, лучше…", "options": ["Сказать сразу", "Сначала всё обдумать", "Написать сообщением", "Дождаться спокойного момента"]},
         {"text": "Во время спора важнее…", "options": ["Найти решение", "Быть услышанным", "Сохранить спокойствие", "Сделать паузу"]},
         {"text": "Как часто хочется переписываться днём?", "options": ["Постоянно", "Несколько раз", "Только по делу", "Лучше поговорить вечером"]},
         {"text": "Лучший способ поддержать?", "options": ["Выслушать", "Дать совет", "Обнять", "Помочь делом"]},
         {"text": "Важные решения принимаем…", "options": ["После долгого обсуждения", "Быстро вместе", "Опираясь на факты", "Доверяя чувствам"]},
         {"text": "Что делает разговор близким?", "options": ["Честность", "Юмор", "Внимание", "Общие мечты"]},
     ]},
    {"title": "Наше будущее ✨",
     "questions": [
         {"text": "Как выглядит идеальный общий дом?", "options": ["Квартира в центре", "Дом за городом", "Жильё у моря", "Главное — быть вместе"]},
         {"text": "Что важнее в ближайшие годы?", "options": ["Карьера", "Семья", "Путешествия", "Финансовая свобода"]},
         {"text": "Большие цели лучше…", "options": ["Подробно планировать", "Обсуждать направление", "Достигать постепенно", "Менять по ситуации"]},
         {"text": "Идеальный ритм жизни через пять лет?", "options": ["Активный городской", "Спокойный семейный", "Много путешествий", "Свободный и гибкий"]},
         {"text": "На что приятнее копить вместе?", "options": ["Свой дом", "Большое путешествие", "Общий проект", "Финансовую подушку"]},
         {"text": "Какая общая мечта вдохновляет сильнее?", "options": ["Создать семью", "Увидеть мир", "Построить уютный дом", "Заниматься любимым делом"]},
     ]},
]

# Тематические паки вопросов со свободными ответами.
# Ответ партнёра виден только когда ответили оба — как в вопросе дня.
PACKS = [
    {"title": "Глубокие разговоры 💬", "description": "Вопросы, которые сближают", "kind": "short",
     "questions": [
        "Чего ты боишься больше всего — и почему?",
        "Какой момент в жизни сильнее всего тебя изменил?",
        "Что бы ты сказал(а) себе 10 лет назад?",
        "Когда ты в последний раз радовался(лась) до слёз?",
        "Какая твоя самая большая гордость?",
        "Что чаще всего тревожит тебя перед сном?",
        "Кого ты считаешь своим главным учителем в жизни?",
        "Что для тебя значит быть любимым(ой)?",
        "О чём ты никогда никому не рассказывал(а)?",
        "Что бы ты изменил(а) в своём прошлом, если бы мог(ла)?",
     ]},
    {"title": "Весёлые и нелепые 😂", "description": "Посмеяться вместе", "kind": "short",
     "questions": [
        "Какая у тебя самая нелепая привычка?",
        "Самый смешной случай из твоего детства?",
        "Если бы ты был(а) супергероем, какая была бы твоя бесполезная суперсила?",
        "Какое блюдо у тебя никогда не получается?",
        "Твоё самое странное сочетание еды?",
        "Самый неловкий момент на свидании?",
        "Если бы мы поменялись телами на день, что бы ты сделал(а) первым?",
        "Какое прозвище тебе давали в школе?",
        "Твой самый глупый страх?",
        "Какая песня гарантированно поднимает тебе настроение?",
     ]},
    {"title": "Будущее и мечты 🔮", "description": "Помечтаем вместе", "kind": "short",
     "questions": [
        "Где ты видишь нас через 5 лет?",
        "О каком доме ты мечтаешь?",
        "Три страны, которые хочешь посетить вместе со мной?",
        "Какая у тебя самая заветная мечта?",
        "Кем ты хотел(а) стать в детстве — и что изменилось?",
        "Какое общее хобби ты бы хотел(а) завести?",
        "Что бы ты сделал(а) с миллионом, если бы мы выиграли его вместе?",
        "Какой навык хочешь освоить в ближайший год?",
        "Идеальный обычный вторник через 10 лет — опиши.",
        "Что ты хочешь, чтобы люди говорили о нас?",
     ]},
    {"title": "Воспоминания 📸", "description": "Тёплое из прошлого", "kind": "short",
     "questions": [
        "Твоё самое раннее воспоминание?",
        "Лучший день рождения в твоей жизни?",
        "Самый счастливый день прошлого года?",
        "Какое место из детства ты бы показал(а) мне?",
        "Что ты подумал(а), когда мы впервые встретились?",
        "Наш лучший совместный день — какой он?",
        "Какая фотография для тебя самая ценная?",
        "О чём напоминает твоя любимая песня из прошлого?",
     ]},
    {"title": "Романтика 💞", "description": "Про нежность", "kind": "short",
     "questions": [
        "Что для тебя идеальный романтический вечер?",
        "Какие слова тебе приятнее всего слышать?",
        "Твой язык любви: слова, время, подарки, забота или прикосновения?",
        "Какой комплимент запомнился тебе на всю жизнь?",
        "Что тебя больше всего привлекает во мне?",
        "Маленький сюрприз, который всегда работает?",
        "Что для тебя значит «скучать»?",
        "Как ты понимаешь, что тебя любят?",
     ]},
    {"title": "Письма друг другу 💌", "description": "Длинные ответы от сердца", "kind": "long",
     "questions": [
        "Напиши письмо партнёру о том, за что ты его любишь.",
        "Опиши ваш идеальный год вместе в деталях.",
        "Расскажи историю вашего знакомства своими словами.",
        "Напиши, каким ты видишь партнёра через 20 лет.",
        "Опиши день, когда ты понял(а), что это — то самое.",
        "Письмо в будущее: что скажешь нам через 10 лет?",
     ]},
    {"title": "Глубокие истории 📖", "description": "Расскажи подробно", "kind": "long",
     "questions": [
        "Расскажи о человеке, который сильнее всего на тебя повлиял.",
        "Опиши самый трудный период жизни и как ты его прошёл.",
        "Какое решение далось тебе тяжелее всего?",
        "Расскажи о своей самой большой мечте подробно.",
        "Опиши место, где ты чувствуешь себя счастливым.",
        "Какой урок жизнь преподала тебе недавно?",
     ]},
    {"title": "Фотозадания 📷", "description": "Отвечай фотографией", "kind": "photo",
     "questions": [
        "Сфотографируй то, что напоминает тебе обо мне.",
        "Твой вид из окна прямо сейчас.",
        "Сфотографируй свой сегодняшний обед.",
        "Что тебя сейчас окружает? Покажи!",
        "Сфотографируй место, где ты чаще всего думаешь о нас.",
        "Твоё отражение сегодня 😉",
        "Покажи небо над тобой.",
        "Сфотографируй то, что тебя сегодня порадовало.",
     ]},
    {"title": "Наши моменты 📸", "description": "Фото и подпись", "kind": "photo",
     "questions": [
        "Поделись любимым совместным фото.",
        "Сфотографируй место вашего последнего свидания.",
        "Покажи вещь, связанную с партнёром.",
        "Сфотографируй свой самый уютный уголок.",
        "Что приготовил(а) вкусного? Покажи!",
        "Твой вечер прямо сейчас — одним кадром.",
     ]},
]

IDEAS = [
    ("Пикник в парке", "Активный отдых", "Бесплатно"),
    ("Домашний кинотеатр с попкорном", "Дома", "Дёшево"),
    ("Прогулка по незнакомому району", "Активный отдых", "Бесплатно"),
    ("Совместная готовка нового блюда", "Дома", "Дёшево"),
    ("Настольные игры вдвоём", "Дома", "Бесплатно"),
    ("Фотосессия друг друга", "Творчество", "Бесплатно"),
    ("Ужин в новом ресторане", "Еда", "Дорого"),
    ("Поход в музей/выставку", "Культура", "Дёшево"),
    ("Велопрогулка за город", "Активный отдых", "Дёшево"),
    ("СПА-вечер дома", "Дома", "Дёшево"),
    ("Караоке-вечер", "Дома", "Бесплатно"),
    ("Поездка на выходные", "Путешествие", "Дорого"),
]

# ---------------- БД ----------------
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    c = con.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        pair_code TEXT UNIQUE NOT NULL,
        partner_id INTEGER,
        together_since TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS moods(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mood TEXT NOT NULL,
        note TEXT DEFAULT '',
        ts TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS answers(
        user_id INTEGER NOT NULL,
        qdate TEXT NOT NULL,
        qindex INTEGER NOT NULL,
        text TEXT NOT NULL,
        ts TEXT NOT NULL,
        PRIMARY KEY(user_id, qdate, qindex));
    CREATE TABLE IF NOT EXISTS quizzes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS quiz_q(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL, text TEXT NOT NULL, options TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS quiz_a(
        user_id INTEGER NOT NULL, quiz_id INTEGER NOT NULL,
        qid INTEGER NOT NULL, option INTEGER NOT NULL,
        PRIMARY KEY(user_id, quiz_id, qid));
    CREATE TABLE IF NOT EXISTS ideas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, category TEXT DEFAULT '',
        budget TEXT DEFAULT '', done INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS journal(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL,
        text TEXT DEFAULT '', ts TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL, date TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS packs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS pack_q(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pack_id INTEGER NOT NULL, text TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS pack_a(
        user_id INTEGER NOT NULL, pack_id INTEGER NOT NULL,
        qid INTEGER NOT NULL, text TEXT NOT NULL, ts TEXT NOT NULL,
        PRIMARY KEY(user_id, pack_id, qid));
    CREATE TABLE IF NOT EXISTS taps(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, ts TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS journal_likes(
        entry_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        PRIMARY KEY(entry_id, user_id));
    CREATE TABLE IF NOT EXISTS widget_photos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, photo TEXT NOT NULL,
        caption TEXT DEFAULT '', ts TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS couple_games(
        pair_key TEXT NOT NULL, kind TEXT NOT NULL,
        state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(pair_key, kind));
    CREATE TABLE IF NOT EXISTS companions(
        pair_key TEXT PRIMARY KEY,
        state TEXT NOT NULL,
        proposal_type TEXT DEFAULT '',
        proposal_name TEXT DEFAULT '',
        proposed_by INTEGER,
        version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS push_tokens(
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        platform TEXT NOT NULL DEFAULT 'android',
        updated_at TEXT NOT NULL);
    """)
    # мягкие миграции для старых БД
    cols_j = [r["name"] for r in c.execute("PRAGMA table_info(journal)").fetchall()]
    if "fav" not in cols_j:
        c.execute("ALTER TABLE journal ADD COLUMN fav INTEGER DEFAULT 0")
    if "photo" not in cols_j:
        c.execute("ALTER TABLE journal ADD COLUMN photo TEXT DEFAULT ''")
    cols_e = [r["name"] for r in c.execute("PRAGMA table_info(events)").fetchall()]
    if "icon" not in cols_e:
        c.execute("ALTER TABLE events ADD COLUMN icon TEXT DEFAULT ''")
    if "repeat" not in cols_e:
        c.execute("ALTER TABLE events ADD COLUMN repeat INTEGER DEFAULT 0")
    cols_u = [r["name"] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    if "birth" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN birth TEXT DEFAULT ''")
    if "avatar" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT ''")
    if "token" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN token TEXT DEFAULT ''")
    if "email" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "password_hash" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "pair_ready" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN pair_ready INTEGER NOT NULL DEFAULT 1")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_uq "
              "ON users(email) WHERE email IS NOT NULL AND email != ''")
    for r in c.execute("SELECT id FROM users WHERE token IS NULL OR token=''").fetchall():
        c.execute("UPDATE users SET token=? WHERE id=?", (new_token(), r["id"]))
    # геопозиция для виджета «расстояние» (хранится только последняя точка)
    c.execute("CREATE TABLE IF NOT EXISTS locations("
              "user_id INTEGER PRIMARY KEY, lat REAL NOT NULL, "
              "lon REAL NOT NULL, ts TEXT NOT NULL)")
    if "premium_until" not in cols_u:
        c.execute("ALTER TABLE users ADD COLUMN premium_until TEXT DEFAULT ''")
    # Telegram-привязка подписки к аккаунту по email.
    c.execute("CREATE TABLE IF NOT EXISTS tg(user_id INTEGER PRIMARY KEY, "
               "tg_id INTEGER UNIQUE, tg_name TEXT DEFAULT '', "
               "ts TEXT DEFAULT '')")
    # Рефералка: кто по чьей ссылке пришёл (rewarded=1 — бонус уже выдан)
    c.execute("CREATE TABLE IF NOT EXISTS refs(tg_id INTEGER PRIMARY KEY, "
              "referrer INTEGER NOT NULL, ts TEXT DEFAULT '', "
              "rewarded INTEGER DEFAULT 0)")
    for q in QUIZZES:
        row = c.execute("SELECT id FROM quizzes WHERE title=?", (q["title"],)).fetchone()
        if row:
            continue
        qid = c.execute("INSERT INTO quizzes(title) VALUES(?)",
                        (q["title"],)).lastrowid
        for qq in q["questions"]:
            c.execute("INSERT INTO quiz_q(quiz_id,text,options) VALUES(?,?,?)",
                      (qid, qq["text"], json.dumps(qq["options"], ensure_ascii=False)))
    if c.execute("SELECT COUNT(*) n FROM ideas").fetchone()["n"] == 0:
        c.executemany("INSERT INTO ideas(title,category,budget) VALUES(?,?,?)", IDEAS)
    cols_p = [r["name"] for r in c.execute("PRAGMA table_info(packs)").fetchall()]
    if "kind" not in cols_p:
        c.execute("ALTER TABLE packs ADD COLUMN kind TEXT DEFAULT 'short'")
    cols_pa = [r["name"] for r in c.execute("PRAGMA table_info(pack_a)").fetchall()]
    if "photo" not in cols_pa:
        c.execute("ALTER TABLE pack_a ADD COLUMN photo TEXT DEFAULT ''")
    for p in PACKS:
        row = c.execute("SELECT id FROM packs WHERE title=?", (p["title"],)).fetchone()
        if row:
            c.execute("UPDATE packs SET kind=? WHERE id=?", (p["kind"], row["id"]))
            continue
        pid = c.execute("INSERT INTO packs(title,description,kind) VALUES(?,?,?)",
                        (p["title"], p["description"], p["kind"])).lastrowid
        c.executemany("INSERT INTO pack_q(pack_id,text) VALUES(?,?)",
                      [(pid, t) for t in p["questions"]])
    con.commit()
    con.close()

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
        threading.Thread(target=run_bot, args=(token,),
                         daemon=True, name="tg-bot").start()

@app.get("/", include_in_schema=False)
def webapp():
    """Мобильное веб-приложение — открыть с телефона по IP компьютера."""
    return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "web", "index.html"))

@app.get("/Enrwine.apk", include_in_schema=False)
def android_app():
    """Текущая Android-версия Enrwine для установки на телефон."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "Enrwine.apk")
    if not os.path.isfile(path):
        path = os.path.join(root, "android", "Enrwine.apk")
    if not os.path.isfile(path):
        raise HTTPException(404, "APK is not available")
    return FileResponse(path, media_type="application/vnd.android.package-archive",
                        filename="Enrwine-1.8.apk")

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

@app.get("/manifest.webmanifest", include_in_schema=False)
def pwa_manifest():
    return FileResponse(os.path.join(WEB_DIR, "manifest.webmanifest"),
                        media_type="application/manifest+json")

@app.get("/sw.js", include_in_schema=False)
def pwa_sw():
    return FileResponse(os.path.join(WEB_DIR, "sw.js"),
                        media_type="application/javascript")

@app.get("/pet3d.html", include_in_schema=False)
def pet3d():
    """3D-питомец (Three.js): уход, комнаты, мини-игры. Прогресс хранится локально в браузере."""
    return FileResponse(os.path.join(WEB_DIR, "pet3d.html"),
                        media_type="text/html")

# ---------------- реалтайм: WebSocket ----------------
class WSManager:
    def __init__(self):
        self.conns: dict = {}

    async def connect(self, ws, uid: int):
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
async def ws_ep(ws: WebSocket, user_id: int, token: str = ""):
    _request_token.set(token or "")
    try:
        me, partner = couple_of(user_id)
    except HTTPException:
        await ws.close()
        return
    await wsman.connect(ws, user_id)
    if partner:
        await wsman.send(partner["id"], {"type": "presence",
                                         "user_id": user_id, "online": True})
    try:
        while True:
            await ws.receive_text()  # keepalive от клиента, игнорируем
    except WebSocketDisconnect:
        pass
    finally:
        wsman.drop(ws, user_id)
        if partner and user_id not in wsman.conns:
            await wsman.send(partner["id"], {"type": "presence",
                                             "user_id": user_id, "online": False})

def today():
    return datetime.date.today().isoformat()

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
        partner = con.execute("SELECT * FROM users WHERE id=?",
                              (me["partner_id"],)).fetchone()
    con.close()
    return me, partner


def couple_of(user_id: int):
    """Пара пользователя + проверка токена текущего запроса.

    Токен выдаётся при создании/входе и хранится на устройстве.
    Без верного X-Auth-Token — 401 (id подряд не перебрать).
    """
    me, partner = lookup_couple(user_id)
    cols = me.keys()
    stored = me["token"] if "token" in cols else ""
    tok = _request_token.get()
    if not stored or not tok or not secrets.compare_digest(stored, tok):
        raise HTTPException(401, "unauthorized")
    return me, partner

def partner_id_of(user_id: int) -> Optional[int]:
    me, partner = lookup_couple(user_id)
    return partner["id"] if partner else None

def touch_streak_days(user_id: int) -> int:
    """Серия: подряд идущие дни с любой активностью (ответ/настроение/запись)."""
    con = db()
    days = set()
    pid = partner_id_of(user_id)
    ids = [user_id] + ([pid] if pid else [])
    q = ",".join("?" * len(ids))
    for r in con.execute(f"SELECT DISTINCT qdate d FROM answers WHERE user_id IN ({q})", ids):
        days.add(r["d"])
    for r in con.execute(f"SELECT DISTINCT substr(ts,1,10) d FROM pack_a WHERE user_id IN ({q})", ids):
        days.add(r["d"])
    for r in con.execute(f"SELECT DISTINCT substr(ts,1,10) d FROM moods WHERE user_id IN ({q})", ids):
        days.add(r["d"])
    for r in con.execute(f"SELECT DISTINCT substr(ts,1,10) d FROM journal WHERE user_id IN ({q})", ids):
        days.add(r["d"])
    con.close()
    d = datetime.date.today()
    if d.isoformat() not in days:
        d -= datetime.timedelta(days=1)
        if d.isoformat() not in days:
            return 0
    streak = 0
    while d.isoformat() in days:
        streak += 1
        d -= datetime.timedelta(days=1)
    return streak

# ---------------- модели ----------------
class PairIn(BaseModel):
    name: str
    birth: str = ""  # YYYY-MM-DD, необязательна (приложение может не слать)
    avatar: str = ""  # URL из POST /photos
    since: str = ""  # дата начала отношений YYYY-MM-DD, иначе сегодня

class JoinIn(BaseModel):
    name: str
    code: str
    birth: str = ""
    avatar: str = ""

class AuthRegisterIn(BaseModel):
    email: str
    password: str

class PairSetupIn(BaseModel):
    user_id: int
    name: str
    birth: str = ""
    avatar: str = ""
    since: str = ""
    partner_code: str = ""

class AuthLoginIn(BaseModel):
    email: str
    password: str

class MoodIn(BaseModel):
    user_id: int
    mood: str
    note: str = ""

class AnswerIn(BaseModel):
    user_id: int
    text: str

class QuizAnswerIn(BaseModel):
    user_id: int
    qid: int
    option: int

class PackAnswerIn(BaseModel):
    user_id: int
    qid: int
    text: str = ""
    photo: str = ""

class IdeaIn(BaseModel):
    title: str
    category: str = ""
    budget: str = ""

class JournalIn(BaseModel):
    user_id: int
    title: str
    text: str = ""
    photo: str = ""  # URL из POST /photos

class EventIn(BaseModel):
    user_id: int
    title: str
    date: str  # YYYY-MM-DD
    icon: str = "🎉"
    repeat: bool = False

class LikeIn(BaseModel):
    user_id: int

class WidgetIn(BaseModel):
    user_id: int
    photo: str
    caption: str = ""

class TapIn(BaseModel):
    user_id: int

class LocationIn(BaseModel):
    user_id: int
    lat: float
    lon: float

class GameActionIn(BaseModel):
    user_id: int
    action: str
    value: Optional[int] = None

class CompanionProposalIn(BaseModel):
    user_id: int
    type: str
    name: str

class CompanionUserIn(BaseModel):
    user_id: int

class CompanionActionIn(BaseModel):
    user_id: int
    action: str
    value: str = ""

class PushTokenIn(BaseModel):
    user_id: int
    token: str
    platform: str = "android"

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

def hash_password(password: str) -> str:
    if not 6 <= len(password) <= 128:
        raise HTTPException(400, "password must contain 6 to 128 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                            n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored.split("$", 2)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode("utf-8"),
                                salt=bytes.fromhex(salt_hex),
                                n=16384, r=8, p=1, dklen=32)
        return secrets.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False

def auth_response(user, token: str):
    return {
        "user_id": user["id"], "pair_code": user["pair_code"],
        "partner_id": user["partner_id"], "token": token,
        "name": user["name"], "birth": user["birth"] or "",
        "avatar": user["avatar"] or "",
        "together_since": user["together_since"],
        "pair_ready": bool(user["pair_ready"]),
    }

def check_birth(birth: str) -> str:
    try:
        bd = datetime.date.fromisoformat(birth)
    except ValueError:
        raise HTTPException(400, "birth must be YYYY-MM-DD")
    if not (datetime.date(1900, 1, 1) <= bd <= datetime.date.today()):
        raise HTTPException(400, "bad birth date")
    return birth

def age_of(birth: str):
    if not birth:
        return None
    b = datetime.date.fromisoformat(birth)
    t = datetime.date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))

def check_since(since: str) -> str:
    """Дата начала отношений: YYYY-MM-DD, от 1900 до сегодня."""
    try:
        d = datetime.date.fromisoformat(since)
    except ValueError:
        raise HTTPException(400, "since must be YYYY-MM-DD")
    if not (datetime.date(1900, 1, 1) <= d <= datetime.date.today()):
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
        cur = con.execute(
            "INSERT INTO users(name,pair_code,together_since,birth,avatar,token,email,password_hash,pair_ready) "
            "VALUES(?,?,?,?,?,?,?,?,0)",
            (email.split("@", 1)[0], new_code(), today(), "", "", token, email, password_hash))
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
def auth_login(body: AuthLoginIn):
    email = normalize_email(body.email)
    if not 6 <= len(body.password) <= 128:
        raise HTTPException(401, "invalid email or password")
    con = db()
    user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not user["password_hash"] or not verify_password(body.password, user["password_hash"]):
        con.close()
        raise HTTPException(401, "invalid email or password")
    token = new_token()
    con.execute("UPDATE users SET token=? WHERE id=?", (token, user["id"]))
    con.commit()
    user = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    con.close()
    _request_token.set(token)
    return auth_response(user, token)

@app.post("/pair/setup")
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
            partner = con.execute("SELECT * FROM users WHERE pair_code=? AND id!=?",
                                  (body.partner_code.strip().upper(), body.user_id)).fetchone()
            if not partner or not partner["pair_ready"]:
                raise HTTPException(404, "code not found")
            if partner["partner_id"]:
                raise HTTPException(400, "code already used")
            since = partner["together_since"]
        else:
            since = check_since(body.since) if body.since else today()

        con.execute(
            "UPDATE users SET name=?,birth=?,avatar=?,together_since=?,partner_id=?,pair_ready=1 WHERE id=?",
            (name, body.birth, body.avatar, since,
             partner["id"] if partner else None, body.user_id))
        if partner:
            con.execute("UPDATE users SET partner_id=? WHERE id=?", (body.user_id, partner["id"]))
        con.commit()
        user = con.execute("SELECT * FROM users WHERE id=?", (body.user_id,)).fetchone()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    if partner:
        await wsman.ping_couple(body.user_id, "pair")
    return auth_response(user, me["token"])

@app.post("/pair")
def pair_create(body: PairIn):
    if body.birth:
        check_birth(body.birth)
    since = check_since(body.since) if body.since else today()
    con = db()
    code = new_code()
    tok = new_token()
    cur = con.execute("INSERT INTO users(name,pair_code,together_since,birth,avatar,token) VALUES(?,?,?,?,?,?)",
                      (body.name.strip(), code, since, body.birth, body.avatar, tok))
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
    other = con.execute("SELECT * FROM users WHERE pair_code=?",
                        (body.code.strip().upper(),)).fetchone()
    if not other:
        con.close()
        raise HTTPException(404, "code not found")
    if other["partner_id"]:
        con.close()
        raise HTTPException(400, "code already used")
    tok = new_token()
    cur = con.execute("INSERT INTO users(name,pair_code,together_since,birth,avatar,token) VALUES(?,?,?,?,?,?)",
                      (body.name.strip(), new_code(), other["together_since"],
                       body.birth, body.avatar, tok))
    uid = cur.lastrowid
    con.execute("UPDATE users SET partner_id=? WHERE id=?", (uid, other["id"]))
    con.execute("UPDATE users SET partner_id=? WHERE id=?", (other["id"], uid))
    con.commit()
    con.close()
    _request_token.set(tok)
    await wsman.ping_couple(uid, "pair")
    return {"user_id": uid, "partner_id": other["id"], "token": tok}

@app.get("/me")
def me(user_id: int):
    me, partner = couple_of(user_id)
    since = datetime.date.fromisoformat(me["together_since"])
    days = (datetime.date.today() - since).days
    mine = None
    con = db()
    r = con.execute("SELECT mood,note,ts FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 1",
                    (user_id,)).fetchone()
    if r:
        mine = dict(r)
    theirs = None
    if partner:
        r = con.execute("SELECT mood,note,ts FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 1",
                        (partner["id"],)).fetchone()
        if r:
            theirs = dict(r)
    con.close()
    return {"id": me["id"], "name": me["name"], "pair_code": me["pair_code"],
            "birth": me["birth"] or "", "avatar": me["avatar"] or "",
            "partner": {"id": partner["id"], "name": partner["name"],
                        "birth": partner["birth"] or "",
                        "avatar": partner["avatar"] or "",
                        "age": age_of(partner["birth"] or "")} if partner else None,
            "days_together": days, "together_since": me["together_since"],
            "streak": touch_streak_days(user_id),
            "my_mood": mine, "partner_mood": theirs}

@app.get("/partner")
def partner_profile(user_id: int):
    """Полный профиль партнёра: аватар, возраст, настроение, активность."""
    me, partner = couple_of(user_id)
    if not partner:
        raise HTTPException(400, "no partner yet")
    pid = partner["id"]
    con = db()
    mood = con.execute("SELECT mood,note,ts FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 1",
                       (pid,)).fetchone()
    answers = con.execute("SELECT COUNT(*) n FROM answers WHERE user_id=?", (pid,)).fetchone()["n"]
    answers += con.execute("SELECT COUNT(*) n FROM pack_a WHERE user_id=?", (pid,)).fetchone()["n"]
    moods = con.execute("SELECT COUNT(*) n FROM moods WHERE user_id=?", (pid,)).fetchone()["n"]
    moments = con.execute("SELECT COUNT(*) n FROM journal WHERE user_id=?", (pid,)).fetchone()["n"]
    taps = con.execute("SELECT COUNT(*) n FROM taps WHERE user_id=?", (pid,)).fetchone()["n"]
    con.close()
    return {"id": pid, "name": partner["name"],
            "avatar": partner["avatar"] or "", "birth": partner["birth"] or "",
            "age": age_of(partner["birth"] or ""),
            "days_together": (datetime.date.today() -
            datetime.date.fromisoformat(me["together_since"])).days,
            "latest_mood": dict(mood) if mood else None,
            "answers": answers, "moods": moods, "moments": moments, "taps": taps}

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
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "firebase-service-account.json"))
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

def send_mood_push(user_id: int, partner_name: str, mood: str):
    messaging = firebase_messaging()
    if messaging is None:
        return
    con = db()
    tokens = [r["token"] for r in con.execute(
        "SELECT token FROM push_tokens WHERE user_id=?", (user_id,)).fetchall()]
    con.close()
    invalid = []
    for token in tokens:
        try:
            messaging.send(messaging.Message(
                notification=messaging.Notification(
                    title=f"Новое настроение от {partner_name}",
                    body=f"Партнёр выбрал настроение {mood}"),
                data={"type": "mood", "mood": mood},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default")),
                token=token))
        except Exception as exc:
            if type(exc).__name__ in ("UnregisteredError", "SenderIdMismatchError"):
                invalid.append(token)
            else:
                print(f"Firebase send failed: {type(exc).__name__}")
    if invalid:
        con = db()
        con.executemany("DELETE FROM push_tokens WHERE token=?",
                        [(token,) for token in invalid])
        con.commit(); con.close()

@app.post("/push/register")
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
        (token, body.user_id, platform,
         datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()
    return {"ok": True}

@app.post("/push/unregister")
def push_unregister(body: PushTokenIn):
    couple_of(body.user_id)
    con = db()
    con.execute("DELETE FROM push_tokens WHERE token=? AND user_id=?",
                (body.token.strip(), body.user_id))
    con.commit(); con.close()
    return {"ok": True}

# ---------------- настроение ----------------
@app.post("/mood")
async def set_mood(body: MoodIn, background_tasks: BackgroundTasks):
    me, partner = couple_of(body.user_id)
    con = db()
    con.execute("INSERT INTO moods(user_id,mood,note,ts) VALUES(?,?,?,?)",
                (body.user_id, body.mood, body.note,
                 datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "mood")
    if partner:
        background_tasks.add_task(
            send_mood_push, partner["id"], me["name"], body.mood)
    return {"ok": True}

# ---------------- ежедневный вопрос ----------------
def daily_question():
    idx = datetime.date.today().toordinal() % len(QUESTIONS)
    return {"date": today(), "index": idx, "text": QUESTIONS[idx]}

@app.get("/daily")
def get_daily(user_id: int):
    couple_of(user_id)
    dq = daily_question()
    con = db()
    pid = partner_id_of(user_id)
    mine = con.execute("SELECT text FROM answers WHERE user_id=? AND qdate=?",
                       (user_id, dq["date"])).fetchone()
    theirs = con.execute("SELECT text FROM answers WHERE user_id=? AND qdate=?",
                         (pid, dq["date"])).fetchone() if pid else None
    con.close()
    # ответ партнёра виден только когда ответили оба
    return {"question": dq,
            "my_answer": mine["text"] if mine else None,
            "partner_answer": theirs["text"] if (mine and theirs) else None,
            "partner_answered": bool(theirs)}

@app.post("/daily/answer")
async def answer_daily(body: AnswerIn):
    user_id = body.user_id
    couple_of(user_id)
    dq = daily_question()
    con = db()
    con.execute("INSERT OR REPLACE INTO answers(user_id,qdate,qindex,text,ts) VALUES(?,?,?,?,?)",
                (user_id, dq["date"], dq["index"], body.text,
                 datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    await wsman.ping_couple(user_id, "daily")
    return {"ok": True}

# ---------------- викторины ----------------
@app.get("/quizzes")
def quizzes():
    con = db()
    rows = con.execute("SELECT id,title FROM quizzes").fetchall()
    out = []
    for r in rows:
        n = con.execute("SELECT COUNT(*) n FROM quiz_q WHERE quiz_id=?", (r["id"],)).fetchone()["n"]
        out.append({"id": r["id"], "title": r["title"], "questions": n})
    con.close()
    return out

@app.get("/quiz/{qid}")
def quiz(qid: int, user_id: int):
    couple_of(user_id)
    con = db()
    q = con.execute("SELECT * FROM quizzes WHERE id=?", (qid,)).fetchone()
    if not q:
        con.close()
        raise HTTPException(404, "quiz not found")
    rows = con.execute("SELECT id,text,options FROM quiz_q WHERE quiz_id=?", (qid,)).fetchall()
    mine = {r["qid"]: r["option"] for r in
            con.execute("SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?", (user_id, qid))}
    pid = partner_id_of(user_id)
    theirs = {r["qid"]: True for r in
              con.execute("SELECT qid FROM quiz_a WHERE user_id=? AND quiz_id=?", (pid, qid))} if pid else {}
    con.close()
    return {"id": q["id"], "title": q["title"],
            "questions": [{"id": r["id"], "text": r["text"],
                           "options": json.loads(r["options"]),
                           "my_option": mine.get(r["id"]),
                           "partner_answered": r["id"] in theirs} for r in rows]}

@app.post("/quiz/{qid}/answer")
async def quiz_answer(qid: int, body: QuizAnswerIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute("SELECT id FROM quiz_q WHERE id=? AND quiz_id=?",
                     (body.qid, qid)).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "question not found")
    con.execute("INSERT OR REPLACE INTO quiz_a(user_id,quiz_id,qid,option) VALUES(?,?,?,?)",
                (body.user_id, qid, body.qid, body.option))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "quiz")
    return {"ok": True}

@app.get("/quiz/{qid}/result")
def quiz_result(qid: int, user_id: int):
    me, partner = couple_of(user_id)
    if not partner:
        raise HTTPException(400, "no partner yet")
    con = db()
    rows = con.execute("SELECT id FROM quiz_q WHERE quiz_id=?", (qid,)).fetchall()
    if not rows:
        con.close()
        raise HTTPException(404, "quiz not found")
    mine = {r["qid"]: r["option"] for r in
            con.execute("SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?", (user_id, qid))}
    theirs = {r["qid"]: r["option"] for r in
              con.execute("SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?",
                          (partner["id"], qid))}
    con.close()
    common = [i for i in mine if i in theirs]
    if not common:
        return {"compatibility": None, "answered_together": 0, "total": len(rows)}
    same = sum(1 for i in common if mine[i] == theirs[i])
    return {"compatibility": round(100 * same / len(common)),
            "answered_together": len(common), "total": len(rows)}

# ---------------- фото на виджет партнёра ----------------
@app.post("/widget")
async def widget_send(body: WidgetIn):
    me, partner = couple_of(body.user_id)
    if not body.photo:
        raise HTTPException(400, "empty photo")
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con = db()
    con.execute("INSERT INTO widget_photos(user_id,photo,caption,ts) VALUES(?,?,?,?)",
                (body.user_id, body.photo, body.caption, now))
    con.execute("DELETE FROM widget_photos WHERE user_id=? AND id NOT IN "
                "(SELECT id FROM widget_photos WHERE user_id=? ORDER BY id DESC LIMIT 20)",
                (body.user_id, body.user_id))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "widget")
    return {"ok": True, "ts": now}

@app.get("/widget")
def widget_latest(user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute("SELECT photo,caption,ts FROM widget_photos WHERE user_id=? "
                       "ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    theirs = con.execute("SELECT photo,caption,ts FROM widget_photos WHERE user_id=? "
                         "ORDER BY id DESC LIMIT 1", (partner["id"],)).fetchone() if partner else None
    con.close()
    return {"mine": dict(mine) if mine else None,
            "partner": dict(theirs) if theirs else None}

# ---------------- смена / удаление пары ----------------
@app.delete("/pair")
async def pair_leave(user_id: int):
    """Покинуть пару, сохранив аккаунты и их действующие сессии."""
    me, partner = couple_of(user_id)
    con = db()
    con.execute("UPDATE users SET partner_id=NULL,pair_ready=0 WHERE id=?", (user_id,))
    con.execute("DELETE FROM locations WHERE user_id=?", (user_id,))
    if partner:
        con.execute("UPDATE users SET partner_id=NULL,pair_ready=0 WHERE id=?", (partner["id"],))
        con.execute("DELETE FROM locations WHERE user_id=?", (partner["id"],))
    con.commit()
    user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    msg = {"type": "reload", "what": "pair"}
    await wsman.send(user_id, msg)
    if partner:
        await wsman.send(partner["id"], msg)
    return auth_response(user, me["token"])

# ---------------- обнимашки (tap-to-feel) ----------------
@app.post("/tap")
async def tap(body: TapIn):
    couple_of(body.user_id)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con = db()
    con.execute("INSERT INTO taps(user_id,ts) VALUES(?,?)", (body.user_id, now))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "tap")
    return {"ok": True, "ts": now}

@app.get("/tap")
def tap_status(user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute("SELECT ts FROM taps WHERE user_id=? ORDER BY id DESC LIMIT 1",
                       (user_id,)).fetchone()
    theirs = con.execute("SELECT ts FROM taps WHERE user_id=? ORDER BY id DESC LIMIT 1",
                         (partner["id"],)).fetchone() if partner else None
    n = con.execute("SELECT COUNT(*) n FROM taps WHERE user_id IN (?,?)",
                    (user_id, partner["id"] if partner else -1)).fetchone()["n"]
    con.close()
    return {"my_last": mine["ts"] if mine else None,
            "partner_last": theirs["ts"] if theirs else None,
            "total": n}

# ---------------- лента настроений ----------------
@app.get("/moods")
def moods_feed(user_id: int):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    q = ",".join("?" * len(ids))
    con = db()
    rows = con.execute(f"SELECT m.mood,m.note,m.ts,u.name author FROM moods m "
                       f"JOIN users u ON u.id=m.user_id WHERE m.user_id IN ({q}) "
                       f"ORDER BY m.id DESC LIMIT 14", ids).fetchall()
    con.close()
    return [dict(r) for r in rows]

# ---------------- активность партнёра ----------------
@app.get("/activity")
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
        (pid, limit)
    ):
        items.append({"id": f"mood:{r['id']}", "type": "mood", "ts": r["ts"],
                      "detail": r["mood"], "extra": r["note"] or "", "photo": ""})

    for r in con.execute(
        "SELECT qdate,qindex,ts FROM answers WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit)
    ):
        items.append({"id": f"daily:{r['qdate']}:{r['qindex']}", "type": "daily",
                      "ts": r["ts"], "detail": "", "extra": "", "photo": ""})

    for r in con.execute(
        "SELECT a.pack_id,a.qid,a.ts,p.title FROM pack_a a "
        "JOIN packs p ON p.id=a.pack_id WHERE a.user_id=? ORDER BY a.ts DESC LIMIT ?",
        (pid, limit)
    ):
        items.append({"id": f"pack:{r['pack_id']}:{r['qid']}", "type": "pack",
                      "ts": r["ts"], "detail": r["title"], "extra": "", "photo": ""})

    for r in con.execute(
        "SELECT id,title,photo,ts FROM journal WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit)
    ):
        items.append({"id": f"journal:{r['id']}", "type": "journal", "ts": r["ts"],
                      "detail": r["title"], "extra": "", "photo": r["photo"] or ""})

    for r in con.execute(
        "SELECT id,ts FROM taps WHERE user_id=? ORDER BY ts DESC LIMIT ?", (pid, limit)
    ):
        items.append({"id": f"tap:{r['id']}", "type": "tap", "ts": r["ts"],
                      "detail": "", "extra": "", "photo": ""})

    for r in con.execute(
        "SELECT id,photo,caption,ts FROM widget_photos WHERE user_id=? ORDER BY ts DESC LIMIT ?",
        (pid, limit)
    ):
        items.append({"id": f"widget:{r['id']}", "type": "widget", "ts": r["ts"],
                      "detail": r["caption"] or "", "extra": "", "photo": r["photo"]})

    con.close()
    items.sort(key=lambda item: item["ts"], reverse=True)
    return {"partner_name": partner["name"], "items": items[:limit]}

# ---------------- статистика пары ----------------
@app.get("/stats")
def stats(user_id: int):
    me, partner = couple_of(user_id)
    pid = partner["id"] if partner else None
    ids = [user_id] + ([pid] if pid else [])
    q = ",".join("?" * len(ids))
    con = db()
    answers = con.execute(f"SELECT COUNT(*) n FROM answers WHERE user_id IN ({q})", ids).fetchone()["n"]
    answers += con.execute(f"SELECT COUNT(*) n FROM pack_a WHERE user_id IN ({q})", ids).fetchone()["n"]
    moods = con.execute(f"SELECT COUNT(*) n FROM moods WHERE user_id IN ({q})", ids).fetchone()["n"]
    moments = con.execute(f"SELECT COUNT(*) n FROM journal WHERE user_id IN ({q})", ids).fetchone()["n"]
    compats = []
    if pid:
        for r in con.execute("SELECT id FROM quizzes").fetchall():
            qs = con.execute("SELECT id FROM quiz_q WHERE quiz_id=?", (r["id"],)).fetchall()
            ma = {x["qid"]: x["option"] for x in con.execute(
                "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?", (user_id, r["id"]))}
            ta = {x["qid"]: x["option"] for x in con.execute(
                "SELECT qid,option FROM quiz_a WHERE user_id=? AND quiz_id=?", (pid, r["id"]))}
            common = [i for i in ma if i in ta]
            if common:
                compats.append(100 * sum(1 for i in common if ma[i] == ta[i]) / len(common))
    con.close()
    return {"days_together": (datetime.date.today() -
            datetime.date.fromisoformat(me["together_since"])).days,
            "streak": touch_streak_days(user_id),
            "answers": answers, "moods": moods, "moments": moments,
            "avg_compatibility": round(sum(compats) / len(compats)) if compats else None,
            "quizzes_together": len(compats)}

# ---------------- тематические паки вопросов ----------------
@app.get("/packs")
def packs(user_id: int, kind: str = ""):
    me, partner = couple_of(user_id)
    pid = partner["id"] if partner else None
    con = db()
    rows = con.execute("SELECT * FROM packs" + (" WHERE kind=?" if kind else ""),
                       (kind,) if kind else []).fetchall()
    out = []
    for p in rows:
        total = con.execute("SELECT COUNT(*) n FROM pack_q WHERE pack_id=?",
                            (p["id"],)).fetchone()["n"]
        my = con.execute("SELECT COUNT(*) n FROM pack_a WHERE user_id=? AND pack_id=?",
                         (user_id, p["id"])).fetchone()["n"]
        together = 0
        if pid:
            together = con.execute(
                "SELECT COUNT(*) n FROM pack_a a JOIN pack_a b "
                "ON a.pack_id=b.pack_id AND a.qid=b.qid "
                "WHERE a.user_id=? AND b.user_id=? AND a.pack_id=?",
                (user_id, pid, p["id"])).fetchone()["n"]
        out.append({"id": p["id"], "title": p["title"],
                    "description": p["description"], "kind": p["kind"],
                    "total": total,
                    "answered_by_me": my, "answered_together": together})
    con.close()
    return out

@app.get("/pack/{pid}")
def pack(pid: int, user_id: int):
    me, partner = couple_of(user_id)
    paid = partner["id"] if partner else None
    con = db()
    p = con.execute("SELECT * FROM packs WHERE id=?", (pid,)).fetchone()
    if not p:
        con.close()
        raise HTTPException(404, "pack not found")
    rows = con.execute("SELECT id,text FROM pack_q WHERE pack_id=?", (pid,)).fetchall()
    mine = {r["qid"]: {"text": r["text"], "photo": r["photo"]} for r in
            con.execute("SELECT qid,text,photo FROM pack_a WHERE user_id=? AND pack_id=?",
                        (user_id, pid))}
    theirs = {r["qid"]: {"text": r["text"], "photo": r["photo"]} for r in
              con.execute("SELECT qid,text,photo FROM pack_a WHERE user_id=? AND pack_id=?",
                          (paid, pid))} if paid else {}
    con.close()
    return {"id": p["id"], "title": p["title"], "description": p["description"],
            "kind": p["kind"],
            "questions": [{"id": r["id"], "text": r["text"],
                           "my_answer": mine.get(r["id"], {}).get("text") if r["id"] in mine else None,
                           "my_photo": mine.get(r["id"], {}).get("photo") if r["id"] in mine else None,
                           "partner_answered": r["id"] in theirs,
                           "partner_answer": theirs[r["id"]]["text"] if r["id"] in mine and r["id"] in theirs else None,
                           "partner_photo": theirs[r["id"]]["photo"] if r["id"] in mine and r["id"] in theirs else None} for r in rows]}

@app.post("/pack/{pid}/answer")
async def pack_answer(pid: int, body: PackAnswerIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute("SELECT id FROM pack_q WHERE id=? AND pack_id=?",
                     (body.qid, pid)).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "question not found")
    if not body.text and not body.photo:
        con.close()
        raise HTTPException(400, "empty answer")
    con.execute("INSERT OR REPLACE INTO pack_a(user_id,pack_id,qid,text,photo,ts) VALUES(?,?,?,?,?,?)",
                (body.user_id, pid, body.qid, body.text, body.photo,
                 datetime.datetime.now().isoformat(timespec="seconds")))
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
        q += " AND category=?"; args.append(category)
    if budget:
        q += " AND budget=?"; args.append(budget)
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

@app.post("/ideas")
async def idea_add(body: IdeaIn):
    con = db()
    cur = con.execute("INSERT INTO ideas(title,category,budget) VALUES(?,?,?)",
                      (body.title, body.category, body.budget))
    con.commit()
    con.close()
    return {"id": cur.lastrowid}

@app.post("/idea/{iid}/done")
async def idea_done(iid: int, done: bool = True):
    con = db()
    con.execute("UPDATE ideas SET done=? WHERE id=?", (1 if done else 0, iid))
    con.commit()
    con.close()
    return {"ok": True}

# ---------------- фото ----------------
PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png",
               "image/webp": ".webp", "image/gif": ".gif"}

@app.post("/photos")
async def upload_photo(file: UploadFile = File(...)):
    # Без авторизации осознанно: загрузка нужна ДО создания аккаунта
    # (аватар при регистрации). Защита — лимит 5 МБ и типы файлов,
    # чтение — только по неугодаемым uuid-ссылкам.
    if file.content_type not in PHOTO_TYPES:
        raise HTTPException(400, "only jpeg/png/webp/gif images")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "max 5MB")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    import uuid as _uuid
    name = _uuid.uuid4().hex + PHOTO_TYPES[file.content_type]
    with open(os.path.join(PHOTO_DIR, name), "wb") as f:
        f.write(data)
    return {"url": f"/photos/{name}"}

@app.get("/photos/{name}")
def get_photo(name: str):
    if not name.replace(".", "").replace("_", "").replace("-", "").isalnum() or "/" in name:
        raise HTTPException(400, "bad name")
    path = os.path.join(PHOTO_DIR, os.path.basename(name))
    if not os.path.isfile(path):
        raise HTTPException(404, "not found")
    return FileResponse(path)

# ---------------- журнал ----------------
@app.post("/journal")
async def journal_add(body: JournalIn):
    couple_of(body.user_id)
    con = db()
    cur = con.execute("INSERT INTO journal(user_id,title,text,photo,ts) VALUES(?,?,?,?,?)",
                      (body.user_id, body.title, body.text, body.photo,
                       datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "journal")
    return {"id": cur.lastrowid}

def journal_row(r, user_id: int, con) -> dict:
    likes = con.execute("SELECT COUNT(*) n FROM journal_likes WHERE entry_id=?",
                        (r["id"],)).fetchone()["n"]
    liked = con.execute("SELECT 1 FROM journal_likes WHERE entry_id=? AND user_id=?",
                        (r["id"], user_id)).fetchone()
    d = dict(r)
    d["likes"] = likes
    d["liked_by_me"] = bool(liked)
    return d

@app.get("/journal")
def journal_list(user_id: int, q: str = "", author: str = "all", fav: bool = False):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    sql = ("SELECT j.*,u.name author FROM journal j JOIN users u ON u.id=j.user_id "
           f"WHERE j.user_id IN ({','.join('?' * len(ids))})")
    args: list = list(ids)
    if author == "me":
        sql += " AND j.user_id=?"; args.append(user_id)
    elif author == "partner" and partner:
        sql += " AND j.user_id=?"; args.append(partner["id"])
    if fav:
        sql += " AND j.fav=1"
    if q:
        sql += " AND (j.title LIKE ? OR j.text LIKE ?)"; args += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY j.fav DESC, j.id DESC"
    con = db()
    rows = con.execute(sql, args).fetchall()
    out = [journal_row(r, user_id, con) for r in rows]
    con.close()
    return out

@app.post("/journal/{jid}/like")
async def journal_like(jid: int, body: LikeIn):
    couple_of(body.user_id)
    con = db()
    ok = con.execute("SELECT id,user_id FROM journal WHERE id=?", (jid,)).fetchone()
    if not ok:
        con.close()
        raise HTTPException(404, "entry not found")
    had = con.execute("SELECT 1 FROM journal_likes WHERE entry_id=? AND user_id=?",
                      (jid, body.user_id)).fetchone()
    if had:
        con.execute("DELETE FROM journal_likes WHERE entry_id=? AND user_id=?",
                    (jid, body.user_id))
        liked = False
    else:
        con.execute("INSERT INTO journal_likes(entry_id,user_id) VALUES(?,?)",
                    (jid, body.user_id))
        liked = True
    likes = con.execute("SELECT COUNT(*) n FROM journal_likes WHERE entry_id=?",
                        (jid,)).fetchone()["n"]
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "journal")
    return {"liked": liked, "likes": likes}

@app.post("/journal/{jid}/fav")
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

@app.delete("/journal/{jid}")
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

@app.post("/events")
async def event_add(body: EventIn):
    couple_of(body.user_id)
    datetime.date.fromisoformat(body.date)  # проверка формата
    con = db()
    cur = con.execute("INSERT INTO events(user_id,title,date,icon,repeat) VALUES(?,?,?,?,?)",
                      (body.user_id, body.title, body.date,
                       body.icon, 1 if body.repeat else 0))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "events")
    return {"id": cur.lastrowid}

@app.get("/events")
def events(user_id: int):
    me, partner = couple_of(user_id)
    ids = [user_id] + ([partner["id"]] if partner else [])
    q = ",".join("?" * len(ids))
    con = db()
    rows = con.execute(f"SELECT * FROM events WHERE user_id IN ({q})", ids).fetchall()
    con.close()
    now = datetime.date.today()
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
        out.append({"id": r["id"], "title": r["title"], "date": show,
                    "days_left": d, "icon": r["icon"] or "🎉",
                    "repeat": bool(r["repeat"])})
    out.sort(key=lambda e: (e["days_left"] < 0, abs(e["days_left"]) if e["days_left"] >= 0 else -e["days_left"]))
    return out

@app.delete("/events/{eid}")
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
        then = datetime.datetime.fromisoformat(ts)
    except ValueError:
        return None
    return max(0, int((datetime.datetime.now() - then).total_seconds() // 60))

@app.post("/location")
async def location_set(body: LocationIn):
    couple_of(body.user_id)  # 404, если пользователя нет
    if not (-90 <= body.lat <= 90 and -180 <= body.lon <= 180):
        raise HTTPException(400, "bad coordinates")
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con = db()
    con.execute("INSERT OR REPLACE INTO locations(user_id,lat,lon,ts) VALUES(?,?,?,?)",
                (body.user_id, round(body.lat, 3), round(body.lon, 3), now))
    con.commit()
    con.close()
    return {"ok": True}

@app.delete("/location")
def location_stop(user_id: int):
    couple_of(user_id)
    con = db()
    con.execute("DELETE FROM locations WHERE user_id=?", (user_id,))
    con.commit()
    con.close()
    return {"ok": True}

@app.get("/distance")
def distance(user_id: int):
    me, partner = couple_of(user_id)
    con = db()
    mine = con.execute("SELECT lat,lon,ts FROM locations WHERE user_id=?",
                       (user_id,)).fetchone()
    theirs = con.execute("SELECT lat,lon,ts FROM locations WHERE user_id=?",
                         (partner["id"],)).fetchone() if partner else None
    con.close()
    out = {"sharing": mine is not None,
           "partner_sharing": theirs is not None,
           "km": None,
           "partner_name": partner["name"] if partner else None,
           "partner_age_min": minutes_ago(theirs["ts"]) if theirs else None}
    if mine is not None and theirs is not None:
        out["km"] = round(haversine_km(mine["lat"], mine["lon"],
                                       theirs["lat"], theirs["lon"]), 1)
    return out

# ---------------- подписка через Telegram-бота ----------------
def premium_active(premium_until: str) -> bool:
    try:
        return bool(premium_until) and datetime.date.fromisoformat(premium_until) >= datetime.date.today()
    except ValueError:
        return False

@app.get("/premium")
def premium_status(user_id: int):
    me, _ = couple_of(user_id)
    until = me["premium_until"] or "" if "premium_until" in me.keys() else ""
    email = me["email"] or "" if "email" in me.keys() else ""
    return {"premium": premium_active(until), "until": until, "email": email}

# ---------------- общая дата «вместе с…» ----------------
# Единый счётчик для обоих: создатель задаёт при создании пары,
# потом любой из пары может поменять — меняется у обоих сразу.
class TogetherIn(BaseModel):
    user_id: int
    date: str  # YYYY-MM-DD

@app.post("/together")
async def together_set(body: TogetherIn):
    me, partner = couple_of(body.user_id)
    date = check_since(body.date)
    con = db()
    con.execute("UPDATE users SET together_since=? WHERE id=?", (date, body.user_id))
    if partner:
        con.execute("UPDATE users SET together_since=? WHERE id=?", (date, partner["id"]))
    con.commit()
    con.close()
    await wsman.ping_couple(body.user_id, "pair")
    days = (datetime.date.today() - datetime.date.fromisoformat(date)).days
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
        "type": "PET", "name": "", "adopted": False,
        "hunger": .72, "joy": .72, "energy": .8, "clean": .8,
        "bond": 0, "level": 1, "xp": 0, "coins": 20,
        "sleeping": False, "timestamp": 0, "lastAction": 0,
        "cooldowns": {}, "day": "", "dailyActions": [],
        "rewardedDay": "", "careDay": "", "streak": 0,
        "room": "rose", "ownedRooms": ["rose"], "accessory": "none",
    }

def normalize_companion(value):
    state = fresh_companion()
    if isinstance(value, dict):
        state.update(value)
    state["type"] = state["type"] if state["type"] in ("PET", "BABY") else "PET"
    state["cooldowns"] = dict(state.get("cooldowns") or {})
    state["dailyActions"] = list(dict.fromkeys(state.get("dailyActions") or []))
    state["ownedRooms"] = list(dict.fromkeys(state.get("ownedRooms") or ["rose"]))
    return state

def companion_day(now_ms: int):
    return datetime.datetime.fromtimestamp(now_ms / 1000).date().isoformat()

def companion_advance(value, now_ms: int):
    state = normalize_companion(value)
    timestamp = int(state.get("timestamp") or 0)
    hours = 0 if not timestamp else min(max(now_ms - timestamp, 0), 24 * 3600000) / 3600000
    sleeping = bool(state.get("sleeping"))
    state["hunger"] = min(1.0, max(.12, float(state["hunger"]) - hours * (.018 if sleeping else .035)))
    state["joy"] = min(1.0, max(.15, float(state["joy"]) - hours * .022))
    state["clean"] = min(1.0, max(.15, float(state["clean"]) - hours * .025))
    state["energy"] = min(1.0, max(.12, float(state["energy"]) + hours * (.4 if sleeping else -.035)))
    state["timestamp"] = max(timestamp, now_ms)
    current_day = companion_day(now_ms)
    if state.get("day") != current_day:
        state["dailyActions"] = []
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
        if not state["sleeping"] and float(state["energy"]) >= .95:
            return state, "Я уже выспался! Давайте поиграем", "idle"
        was_sleeping = bool(state["sleeping"])
        state["sleeping"] = not was_sleeping
        state["lastAction"] = now_ms
        return state, ("Доброе утро!" if was_sleeping else
                       "Тихий час · энергия растёт даже после закрытия приложения"), ("love" if was_sleeping else "sleep")
    if state["sleeping"]:
        return state, "Сначала разбудите малыша — пусть откроет глазки", "idle"
    remaining = int(state["cooldowns"].get(action, 0)) - now_ms + 45000
    if remaining > 0:
        return state, f"Ещё {(remaining + 999) // 1000} с — можно попробовать другое действие", "idle"
    if action == "feed":
        if float(state["hunger"]) >= .92:
            return state, "Животик полон — покормите немного позже", "idle"
        state["hunger"] = min(1.0, float(state["hunger"]) + .25)
        state["joy"] = min(1.0, float(state["joy"]) + .03)
    elif action == "play":
        if float(state["energy"]) < .25:
            return state, "Сначала поспим: для игры нужна энергия", "idle"
        if float(state["hunger"]) < .2:
            return state, "Сначала перекусим, а потом поиграем", "idle"
        if float(state["joy"]) >= .95:
            return state, "Я счастлив! Давай немного отдохнём", "idle"
        state["joy"] = min(1.0, float(state["joy"]) + .24)
        state["energy"] = max(.12, float(state["energy"]) - .12)
        state["hunger"] = max(.12, float(state["hunger"]) - .07)
        state["clean"] = max(.15, float(state["clean"]) - .06)
    elif action == "wash":
        if float(state["clean"]) >= .95:
            return state, "Уже чистенький! Можно обнять", "idle"
        state["clean"] = 1.0
        state["joy"] = min(1.0, float(state["joy"]) + .04)
    elif action == "love":
        state["joy"] = min(1.0, float(state["joy"]) + .06)
        state["bond"] = min(100, int(state["bond"]) + 1)
    else:
        return state, "Неизвестное действие", "idle"

    current_day = companion_day(now_ms)
    yesterday = (datetime.datetime.fromtimestamp(now_ms / 1000).date() -
                 datetime.timedelta(days=1)).isoformat()
    actions = list(dict.fromkeys([*state["dailyActions"], action]))
    daily_reward = len(actions) >= 3 and state.get("rewardedDay") != current_day
    old_level = int(state["level"])
    state["xp"] = int(state["xp"]) + (3 if action == "love" else 10)
    state["coins"] = int(state["coins"]) + (0 if action == "love" else 2) + (15 if daily_reward else 0)
    state["dailyActions"] = actions
    if daily_reward:
        state["rewardedDay"] = current_day
    if state.get("careDay") != current_day:
        state["streak"] = int(state["streak"]) + 1 if state.get("careDay") == yesterday else 1
    state["careDay"] = current_day
    state["cooldowns"][action] = now_ms
    state["lastAction"] = now_ms
    while int(state["level"]) < 10 and int(state["xp"]) >= companion_required_xp(int(state["level"])):
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
        message = {"feed": "Ням! Спасибо за вкусный обед",
                   "wash": "Пузырьки! Теперь я чистенький",
                   "play": "Ура! Обожаю играть с тобой",
                   "love": "Как хорошо рядом с тобой ♥"}[action]
    return state, message, action

def companion_response(row, state, version: int, user_id: int,
                       message: str = "", animation: str = "idle"):
    proposal = None
    if row and row["proposal_type"]:
        proposal = {"type": row["proposal_type"], "name": row["proposal_name"],
                    "proposed_by": row["proposed_by"],
                    "is_mine": row["proposed_by"] == user_id}
    return {"state": state, "version": version, "proposal": proposal,
            "message": message, "animation": animation}

@app.get("/companion")
def companion_get(user_id: int):
    _, _, pair_key = companion_couple(user_id)
    con = db()
    row = con.execute("SELECT * FROM companions WHERE pair_key=?", (pair_key,)).fetchone()
    con.close()
    state = companion_advance(json.loads(row["state"]), int(datetime.datetime.now().timestamp() * 1000)) if row else fresh_companion()
    return companion_response(row, state, row["version"] if row else 0, user_id)

@app.post("/companion/propose")
async def companion_propose(body: CompanionProposalIn):
    _, _, pair_key = companion_couple(body.user_id)
    pet_type = body.type.strip().upper()
    name = body.name.strip()
    if pet_type not in ("PET", "BABY"):
        raise HTTPException(400, "invalid companion type")
    if not name or len(name) > 24:
        raise HTTPException(400, "invalid companion name")
    con = db()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute("SELECT * FROM companions WHERE pair_key=?", (pair_key,)).fetchone()
    state = normalize_companion(json.loads(row["state"])) if row else fresh_companion()
    if state["adopted"]:
        con.rollback(); con.close()
        raise HTTPException(409, "companion already adopted")
    version = (row["version"] if row else 0) + 1
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con.execute("INSERT OR REPLACE INTO companions(pair_key,state,proposal_type,proposal_name,proposed_by,version,updated_at) VALUES(?,?,?,?,?,?,?)",
                (pair_key, json.dumps(state), pet_type, name, body.user_id, version, now))
    con.commit()
    row = con.execute("SELECT * FROM companions WHERE pair_key=?", (pair_key,)).fetchone()
    con.close()
    await wsman.ping_couple(body.user_id, "companion")
    return companion_response(row, state, version, body.user_id,
                              "Предложение отправлено партнёру")

@app.post("/companion/confirm")
async def companion_confirm(body: CompanionUserIn):
    _, _, pair_key = companion_couple(body.user_id)
    con = db()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute("SELECT * FROM companions WHERE pair_key=?", (pair_key,)).fetchone()
    if not row or not row["proposal_type"]:
        con.rollback(); con.close()
        raise HTTPException(409, "no companion proposal")
    if row["proposed_by"] == body.user_id:
        con.rollback(); con.close()
        raise HTTPException(409, "partner must confirm the proposal")
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    state = fresh_companion()
    state.update({"type": row["proposal_type"], "name": row["proposal_name"],
                  "adopted": True, "timestamp": now_ms})
    version = row["version"] + 1
    con.execute("UPDATE companions SET state=?,proposal_type='',proposal_name='',proposed_by=NULL,version=?,updated_at=? WHERE pair_key=?",
                (json.dumps(state), version, datetime.datetime.now().isoformat(timespec="seconds"), pair_key))
    con.commit(); con.close()
    await wsman.ping_couple(body.user_id, "companion")
    return companion_response(None, state, version, body.user_id,
                              f"{state['name']} теперь живёт у вас!", "love")

@app.post("/companion/action")
async def companion_action(body: CompanionActionIn):
    _, _, pair_key = companion_couple(body.user_id)
    con = db()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute("SELECT * FROM companions WHERE pair_key=?", (pair_key,)).fetchone()
    if not row:
        con.rollback(); con.close()
        raise HTTPException(409, "choose a companion first")
    state = normalize_companion(json.loads(row["state"]))
    if not state["adopted"]:
        con.rollback(); con.close()
        raise HTTPException(409, "choose a companion first")
    message, animation = "", "idle"
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    if body.action in ("feed", "play", "wash", "love", "sleep"):
        state, message, animation = companion_care(state, body.action, now_ms)
    elif body.action == "room":
        room = body.value
        if room not in COMPANION_ROOMS:
            con.rollback(); con.close()
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
            con.rollback(); con.close()
            raise HTTPException(400, "accessory not found")
        if int(state["level"]) < levels[body.value]:
            con.rollback(); con.close()
            raise HTTPException(409, "accessory is locked")
        state["accessory"], message = body.value, "Украшение выбрано"
    elif body.action == "rename":
        name = body.value.strip()
        if not name or len(name) > 24:
            con.rollback(); con.close()
            raise HTTPException(400, "invalid companion name")
        state["name"], message = name, "Новое имя сохранено"
    elif body.action == "reset":
        state, message = fresh_companion(), "Можно выбрать нового друга вместе"
    else:
        con.rollback(); con.close()
        raise HTTPException(400, "bad action")
    version = row["version"] + 1
    con.execute("UPDATE companions SET state=?,proposal_type='',proposal_name='',proposed_by=NULL,version=?,updated_at=? WHERE pair_key=?",
                (json.dumps(state), version, datetime.datetime.now().isoformat(timespec="seconds"), pair_key))
    con.commit(); con.close()
    await wsman.ping_couple(body.user_id, "companion")
    return companion_response(None, state, version, body.user_id, message, animation)

# ---------------- онлайн-игры для пары ----------------
SYNC_ROUNDS = [
    ("Идеальный вечер вдвоём?", ["Кино дома", "Прогулка", "Ресторан", "Приключение"]),
    ("Куда сорвёмся на выходные?", ["К морю", "В горы", "В новый город", "Останемся дома"]),
    ("Какой сюрприз приятнее?", ["Письмо", "Подарок", "Свидание", "Завтрак в постель"]),
    ("Наш общий супернавык?", ["Смешить", "Поддерживать", "Путешествовать", "Создавать уют"]),
    ("Что выберем прямо сейчас?", ["Обниматься", "Гулять", "Готовить", "Играть"]),
    ("Как выглядит идеальное утро?", ["Спать долго", "Кофе в кровать", "Спорт", "Раннее путешествие"]),
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
    base = {"kind": kind, "waiting": partner is None,
            "partner_name": partner["name"] if partner else None, "version": version}
    if partner is None:
        return base
    if kind == "tic_tac_toe":
        return {**base, "board": state["board"], "turn": state.get("turn"),
                "winner": state.get("winner"), "draw": bool(state.get("draw", False)),
                "my_symbol": "X" if me["id"] == min(me["id"], partner["id"]) else "O",
                "my_turn": state.get("turn") == me["id"],
                "result": "win" if state.get("winner") == me["id"] else
                          "lose" if state.get("winner") == partner["id"] else
                          "draw" if state.get("draw") else "playing"}
    idx = int(state.get("round", 0)) % len(SYNC_ROUNDS)
    prompt, options = SYNC_ROUNDS[idx]
    picks = state.get("picks", {})
    mine, theirs = picks.get(str(me["id"])), picks.get(str(partner["id"]))
    revealed = bool(state.get("revealed", False))
    return {**base, "round": int(state.get("round", 0)), "prompt": prompt,
            "options": options, "my_choice": mine, "partner_chosen": theirs is not None,
            "partner_choice": theirs if revealed else None, "score": int(state.get("score", 0)),
            "revealed": revealed}

@app.get("/games/{kind}")
def game_get(kind: str, user_id: int):
    me, partner, pair_key = game_couple(user_id)
    if not partner:
        return game_response(kind, fresh_game(kind, me["id"]), 0, me, partner)
    con = db()
    row = con.execute("SELECT state,version FROM couple_games WHERE pair_key=? AND kind=?",
                      (pair_key, kind)).fetchone()
    if row:
        state, version = json.loads(row["state"]), row["version"]
    else:
        state, version = fresh_game(kind, min(me["id"], partner["id"])), 1
        con.execute("INSERT INTO couple_games(pair_key,kind,state,version,updated_at) VALUES(?,?,?,?,?)",
                    (pair_key, kind, json.dumps(state), version,
                     datetime.datetime.now().isoformat(timespec="seconds")))
        con.commit()
    con.close()
    return game_response(kind, state, version, me, partner)

@app.post("/games/{kind}/action")
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
    row = con.execute("SELECT state,version FROM couple_games WHERE pair_key=? AND kind=?",
                      (pair_key, kind)).fetchone()
    state = json.loads(row["state"]) if row else fresh_game(kind, min(me["id"], partner["id"]))
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
            wins = ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
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
            if value is None or value not in range(len(SYNC_ROUNDS[int(state.get("round", 0)) % len(SYNC_ROUNDS)][1])):
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
            state = {"round": int(state.get("round", 0)) + 1, "picks": {},
                     "score": int(state.get("score", 0)), "revealed": False}
        elif body.action == "reset":
            state = fresh_game(kind, min(me["id"], partner["id"]))
        else:
            reject(400, "bad action")
    else:
        reject(404, "unknown game")
    version += 1
    con.execute("INSERT OR REPLACE INTO couple_games(pair_key,kind,state,version,updated_at) VALUES(?,?,?,?,?)",
                (pair_key, kind, json.dumps(state), version,
                 datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()
    await wsman.ping_couple(body.user_id, "game")
    return game_response(kind, state, version, me, partner)


# Keep this mount last so API, WebSocket, photos and APK routes take priority.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="flutter_web")
