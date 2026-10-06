"""Telegram-бот подписки CoupleJoy: привязка кода + оплата Stars.

Запуск: импортируется из main.py (threading в startup) при заданном
TELEGRAM_BOT_TOKEN. Только стандартная библиотека, зависимостей нет.

Переменные окружения:
  TELEGRAM_BOT_TOKEN — токен от @BotFather (обязательно для запуска)
  TELEGRAM_BOT_NAME  — username бота без @ (для ссылок, по умолчанию Enrwine_bot)
  PREMIUM_STARS      — цена в Stars за период (по умолчанию 99)
  PREMIUM_DAYS       — дней Premium за оплату (по умолчанию 30)
  COUPLE_DB          — путь к базе (как у main.py)
"""
import datetime
import json
import os
import sqlite3
import time
import urllib.request

API = "https://api.telegram.org/bot"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("COUPLE_DB", os.path.join(BASE_DIR, "couple.db"))
BOT_NAME = os.environ.get("TELEGRAM_BOT_NAME", "Enrwine_bot")
PRICE_STARS = int(os.environ.get("PREMIUM_STARS", "99"))
PREMIUM_DAYS = int(os.environ.get("PREMIUM_DAYS", "30"))
APP_URL = os.environ.get("APP_PUBLIC_URL", "https://ssssw-sladaqqq.amvera.io")
ICON_URL = APP_URL.rstrip("/") + "/icons/icon-512.png"


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def api(token, method, payload=None, timeout=65):
    url = API + token + "/" + method
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def send(token, chat, text, buttons=None):
    kb = None
    if buttons:
        kb = {"keyboard": [[{"text": b} for b in row] for row in buttons],
              "resize_keyboard": True}
    payload = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    if kb:
        payload["reply_markup"] = kb
    try:
        api(token, "sendMessage", payload)
    except Exception:
        pass


def safe(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_welcome(token, chat):
    try:
        api(token, "sendPhoto", {
            "chat_id": chat, "photo": ICON_URL,
            "caption": "<b>💞 CoupleJoy Premium</b>\nПодписка для двоих — темы вопросов, "
                       "фото на виджет и новые функции.",
            "parse_mode": "HTML"})
    except Exception:
        pass


def grant_premium(user_id, days=PREMIUM_DAYS):
    con = db()
    row = con.execute("SELECT premium_until FROM users WHERE id=?",
                      (user_id,)).fetchone()
    try:
        cur = datetime.date.fromisoformat(row["premium_until"])
    except (ValueError, TypeError):
        cur = None
    start = max(datetime.date.today(), cur) if cur else datetime.date.today()
    until = (start + datetime.timedelta(days=days)).isoformat()
    con.execute("UPDATE users SET premium_until=? WHERE id=?",
                (until, user_id))
    con.commit()
    con.close()
    return until


def link_code(tg_id, tg_name, code):
    """Привязка chat-id по коду из приложения. Возвращает (ok, текст, user_id)."""
    code = (code or "").strip().upper()
    con = db()
    row = con.execute("SELECT user_id FROM tg WHERE code=?", (code,)).fetchone()
    if not row and code:
        con.close()
        return False, "Код не найден. Возьми свежий код в приложении: Ещё → Premium.", None
    if not row:
        con.close()
        return False, "Пришли код из приложения: Ещё → Premium → «Показать код».", None
    uid = row["user_id"]
    con.execute("UPDATE tg SET tg_id=?, tg_name=?, code='' WHERE user_id=?",
                (tg_id, tg_name, uid))
    con.commit()
    user = con.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    aname = safe(user["name"]) if user else str(uid)
    return True, (f"✅ <b>Готово!</b> Привязано к аккаунту «{aname}».\n"
                 f"Нажми «Купить Premium 💫» — подписка за минуту ⭐"), uid


def user_by_tg(tg_id):
    con = db()
    row = con.execute("SELECT user_id FROM tg WHERE tg_id=?", (tg_id,)).fetchone()
    con.close()
    return row["user_id"] if row else None


def premium_until(user_id):
    con = db()
    row = con.execute("SELECT premium_until FROM users WHERE id=?",
                      (user_id,)).fetchone()
    con.close()
    return row["premium_until"] if row else ""


MENU = [["Купить Premium 💫", "Мой статус ⭐"]]


def handle_message(token, m):
    chat = m["chat"]["id"]
    tg_name = safe((m["chat"].get("first_name") or "").strip())
    text = (m.get("text") or "").strip()
    if "successful_payment" in m:
        uid = user_by_tg(chat)
        if uid:
            until = grant_premium(uid)
            send(token, chat,
                 f"✅ <b>Оплата прошла!</b>\n\n💫 Premium активен до <b>{until}</b>.\n"
                 f"Открой приложение и нажми «Обновить статус» — функции уже разблокированы 💞",
                 MENU)
        else:
            send(token, chat,
                 "Оплата прошла, но аккаунт не привязан. Пришли код из приложения "
                 "(Ещё → Premium → «Показать код»).", MENU)
        return
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            ok, msg, _ = link_code(chat, tg_name, parts[1])
            send(token, chat, msg if ok else "❌ " + msg, MENU)
        else:
            uid = user_by_tg(chat)
            if not uid:
                send_welcome(token, chat)
            send(token, chat,
                 ("✅ <b>Ты уже привязан.</b> Нажми «Купить Premium 💫» — и всё твоё."
                  if uid else
                  "<b>Привет! Это бот подписки CoupleJoy 💞</b>\n\n"
                  "1️⃣ Возьми код в приложении: <b>Ещё → Premium → «Показать код»</b>\n"
                  "2️⃣ Пришли код сюда (или перейди по кнопке «Открыть бота» — код подставится сам)\n"
                  "3️⃣ Нажми «Купить Premium 💫» и оплати звёздами ⭐"),
                 MENU)
        return
    if text == "Мой статус ⭐":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                 "Сначала привяжи аккаунт:\n1️⃣ Возьми код в приложении (<b>Ещё → Premium</b>)\n"
                 "2️⃣ Пришли его сюда.", MENU)
            return
        until = premium_until(uid) or ""
        try:
            active = bool(until) and datetime.date.fromisoformat(until) >= datetime.date.today()
        except ValueError:
            active = False
        send(token, chat,
             f"💫 <b>Premium активен до {until}</b> ✅\nПриятного пользования вдвоём 💞"
             if active else
             "Premium не активен 😔\nНажми «Купить Premium 💫» — это минута.",
             MENU)
        return
    if text == "Купить Premium 💫":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                 "Сначала привяжи аккаунт: пришли код из приложения (<b>Ещё → Premium</b>).",
                 MENU)
            return
        try:
            api(token, "sendInvoice", {
                "chat_id": chat,
                "title": "💫 CoupleJoy Premium",
                "description": f"Темы вопросов, фото на виджет и новые функции на {PREMIUM_DAYS} дней",
                "payload": f"prem:{uid}",
                "currency": "XTR",
                "prices": [{"label": f"Premium {PREMIUM_DAYS} дн.", "amount": PRICE_STARS}],
            })
        except Exception:
            send(token, chat,
                 "Не получилось выставить счёт 😔 Попробуй чуть позже.", MENU)
        return
    # всё остальное считаем кодом привязки
    if text:
        ok, msg, _ = link_code(chat, tg_name, text)
        send(token, chat, msg if ok else "❌ " + msg, MENU)


def run_bot(token):
    offset = 0
    while True:
        try:
            upd = api(token, "getUpdates",
                      {"offset": offset, "timeout": 50, "allowed_updates":
                       ["message", "pre_checkout_query"]}, timeout=70)
        except Exception:
            time.sleep(5)
            continue
        for u in upd.get("result", []):
            offset = max(offset, u.get("update_id", 0) + 1)
            try:
                if "pre_checkout_query" in u:
                    q = u["pre_checkout_query"]
                    ok = (q.get("invoice_payload") or "").startswith("prem:")
                    api(token, "answerPreCheckoutQuery",
                        {"pre_checkout_query_id": q["id"], "ok": ok})
                elif "message" in u:
                    handle_message(token, u["message"])
            except Exception:
                continue
