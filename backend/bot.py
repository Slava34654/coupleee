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
    try:
        api(token, "sendMessage", {"chat_id": chat, "text": text,
                                  "reply_markup": kb} if kb else
            {"chat_id": chat, "text": text})
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
    return True, f"Привязано к аккаунту «{user['name'] if user else uid}». Теперь можно покупать Premium 💫", uid


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
    tg_name = (m["chat"].get("first_name") or "").strip()
    text = (m.get("text") or "").strip()
    if "successful_payment" in m:
        uid = user_by_tg(chat)
        if uid:
            until = grant_premium(uid)
            send(token, chat,
                 f"Оплата прошла ✅ Premium активен до {until}.\n"
                 f"Открой приложение — функции разблокированы 💞", MENU)
        else:
            send(token, chat,
                 "Оплата прошла, но аккаунт не привязан. Пришли код из приложения.", MENU)
        return
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            ok, msg, _ = link_code(chat, tg_name, parts[1])
            send(token, chat, ("✅ " if ok else "❌ ") + msg, MENU)
        else:
            uid = user_by_tg(chat)
            send(token, chat,
                 ("Ты уже привязан ✅ Нажми «Купить Premium 💫»."
                  if uid else
                  "Привет! Это бот подписки CoupleJoy 💞\n"
                  "Возьми код в приложении (Ещё → Premium) и пришли его сюда — "
                  "можно просто перейти по кнопке из приложения."),
                 MENU)
        return
    if text == "Мой статус ⭐":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat, "Сначала привяжи аккаунт: пришли код из приложения.", MENU)
            return
        until = premium_until(uid) or ""
        try:
            active = bool(until) and datetime.date.fromisoformat(until) >= datetime.date.today()
        except ValueError:
            active = False
        send(token, chat,
             f"Premium активен до {until} ✅" if active else
             "Premium не активен. Нажми «Купить Premium 💫».", MENU)
        return
    if text == "Купить Premium 💫":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat, "Сначала привяжи аккаунт: пришли код из приложения.", MENU)
            return
        try:
            api(token, "sendInvoice", {
                "chat_id": chat,
                "title": "CoupleJoy Premium",
                "description": f"Все функции на {PREMIUM_DAYS} дней",
                "payload": f"prem:{uid}",
                "currency": "XTR",
                "prices": [{"label": f"Premium {PREMIUM_DAYS} дн.", "amount": PRICE_STARS}],
            })
        except Exception:
            send(token, chat,
                 "Не получилось выставить счёт. Попробуй позже.", MENU)
        return
    # всё остальное считаем кодом привязки
    if text:
        ok, msg, _ = link_code(chat, tg_name, text)
        send(token, chat, ("✅ " if ok else "❌ ") + msg, MENU)


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
