"""Telegram-бот подписки Enrwine: привязка кода + оплата.

Запуск: импортируется из main.py (threading в startup) при заданном
TELEGRAM_BOT_TOKEN. Только стандартная библиотека, зависимостей нет.

Переменные окружения:
  TELEGRAM_BOT_TOKEN — токен от @BotFather (обязательно для запуска)
  TELEGRAM_BOT_NAME  — username бота без @ (для ссылок, по умолчанию Enrwine_bot)
  PREMIUM_DAYS       — дней Premium за оплату (по умолчанию 30)
  PAYMENT_URL        — ссылка на оплату в банке
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
PREMIUM_DAYS = int(os.environ.get("PREMIUM_DAYS", "30"))
PAYMENT_URL = os.environ.get(
    "PAYMENT_URL",
    "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79333335415&bankCode=100000000111",
)
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_TG_IDS", "").split(",") if x.strip().isdigit()}
REF_BONUS = int(os.environ.get("REF_BONUS_DAYS", "7"))
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


def send_payment(token, chat, uid):
    payload = {
        "chat_id": chat,
        "text": (f"💫 <b>Enrwine Premium на {PREMIUM_DAYS} дней</b>\n\n"
                 "Нажми кнопку ниже для оплаты через СберБанк. "
                 "После оплаты отправь чек администратору для активации Premium.\n\n"
                 f"Номер аккаунта: <code>{uid}</code>"),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{
                "text": "Оплатить в СберБанке",
                "url": PAYMENT_URL,
            }]],
        },
    }
    try:
        api(token, "sendMessage", payload)
    except Exception:
        send(token, chat, f"Ссылка для оплаты:\n{PAYMENT_URL}", MENU)


def safe(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_welcome(token, chat):
    try:
        api(token, "sendPhoto", {
            "chat_id": chat, "photo": ICON_URL,
            "caption": "<b>💞 Enrwine Premium</b>\nПодписка для двоих — темы вопросов, "
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
                 f"Нажми «Купить Premium 💫» для оплаты"), uid


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


MENU = [["Купить Premium 💫", "Мой статус ⭐"], ["Пригласить друга 💌"]]


def ref_link(uid):
    return f"https://t.me/{BOT_NAME}?start=ref_{uid}"


def record_ref(tg_id, referrer_uid):
    """Запомнить, что tg_id пришёл по ссылке пользователя referrer_uid.
    Возвращает ok/self/nouser/already."""
    con = db()
    me = con.execute("SELECT user_id FROM tg WHERE tg_id=?", (tg_id,)).fetchone()
    if me and me["user_id"] == referrer_uid:
        con.close()
        return "self"
    if not con.execute("SELECT 1 FROM users WHERE id=?", (referrer_uid,)).fetchone():
        con.close()
        return "nouser"
    if con.execute("SELECT 1 FROM refs WHERE tg_id=?", (tg_id,)).fetchone():
        con.close()
        return "already"
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con.execute("INSERT INTO refs(tg_id,referrer,ts) VALUES(?,?,?)",
                (tg_id, referrer_uid, now))
    con.commit()
    con.close()
    return "ok"


def reward_referrer(payer_tg_id):
    """Бонус пригласившему за ОПЛАТУ. Возвращает (tg_id_реферера|None, until)."""
    con = db()
    r = con.execute("SELECT referrer FROM refs WHERE tg_id=? AND rewarded=0",
                    (payer_tg_id,)).fetchone()
    con.close()
    if not r:
        return None
    until = grant_premium(r["referrer"], REF_BONUS)
    con = db()
    con.execute("UPDATE refs SET rewarded=1 WHERE tg_id=?", (payer_tg_id,))
    con.commit()
    rt = con.execute("SELECT tg_id FROM tg WHERE user_id=?", (r["referrer"],)).fetchone()
    con.close()
    return (rt["tg_id"] if rt and rt["tg_id"] else None), until


def ref_stats(uid):
    con = db()
    inv = con.execute("SELECT COUNT(*) n FROM refs WHERE referrer=?", (uid,)).fetchone()["n"]
    earn = con.execute("SELECT COUNT(*) n FROM refs WHERE referrer=? AND rewarded=1",
                       (uid,)).fetchone()["n"]
    con.close()
    return inv, earn


def is_admin(tg_id):
    return tg_id in ADMIN_IDS


def find_user(key):
    """Поиск пользователя по id или коду пары. Возвращает (id, name) или None."""
    key = (key or "").strip()
    con = db()
    row = None
    if key.isdigit():
        row = con.execute("SELECT id, name FROM users WHERE id=?",
                          (int(key),)).fetchone()
    if row is None and key:
        row = con.execute("SELECT id, name FROM users WHERE pair_code=?",
                          (key.upper(),)).fetchone()
    con.close()
    return (row["id"], row["name"]) if row else None


def admin_grant(key, days):
    found = find_user(key)
    if not found:
        return "Пользователь не найден. Пришли id или код пары."
    uid, name = found
    until = grant_premium(uid, days)
    return f"✅ <b>{safe(name)}</b> (id {uid}) — Premium до <b>{until}</b>."


def admin_revoke(key):
    found = find_user(key)
    if not found:
        return "Пользователь не найден. Пришли id или код пары."
    uid, name = found
    con = db()
    con.execute("UPDATE users SET premium_until='' WHERE id=?", (uid,))
    con.commit()
    con.close()
    return f"Premium у <b>{safe(name)}</b> (id {uid}) выключен."


def admin_users():
    con = db()
    rows = con.execute(
        "SELECT id, name, premium_until FROM users ORDER BY id DESC LIMIT 10").fetchall()
    con.close()
    today = datetime.date.today().isoformat()
    lines = []
    for r in rows:
        mark = "💫" if r["premium_until"] and r["premium_until"] >= today else "–"
        lines.append(f"{mark} <b>{safe(r['name'])}</b> (id {r['id']})"
                     + (f" до {r['premium_until']}" if r["premium_until"] else ""))
    return "Последние пользователи:\n" + "\n".join(lines) if lines else "Пока пусто."


def admin_stats():
    con = db()
    users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    today = datetime.date.today().isoformat()
    prem = con.execute("SELECT COUNT(*) n FROM users WHERE premium_until >= ?",
                       (today,)).fetchone()["n"]
    sharing = con.execute("SELECT COUNT(*) n FROM locations").fetchone()["n"]
    con.close()
    return (f"📊 <b>Статистика</b>\nПользователей: {users}\n"
            f"С Premium: {prem}\nДелятся геопозицией: {sharing}")


def handle_message(token, m):
    chat = m["chat"]["id"]
    tg_name = safe((m["chat"].get("first_name") or "").strip())
    text = (m.get("text") or "").strip()
    if text.startswith("/grant ") or text.startswith("/ungrant ") or text in (
            "/users", "/stats", "/admin"):
        if not is_admin(chat):
            send(token, chat, "Нет доступа 🔒", MENU)
            return
        parts = text.split()
        cmd = parts[0]
        if cmd == "/grant":
            days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 365
            key = parts[1] if len(parts) > 1 else ""
            send(token, chat, admin_grant(key, days) if key else
                 "Формат: <code>/grant КОД_ПАРЫ [дней]</code>\nПример: <code>/grant A1B2C3 365</code>",
                 MENU)
        elif cmd == "/ungrant":
            key = parts[1] if len(parts) > 1 else ""
            send(token, chat, admin_revoke(key) if key else
                 "Формат: <code>/ungrant КОД_ПАРЫ</code>", MENU)
        elif cmd == "/users":
            send(token, chat, admin_users(), MENU)
        elif cmd == "/stats":
            send(token, chat, admin_stats(), MENU)
        else:
            send(token, chat,
                 "🔧 <b>Админка</b>\n<code>/grant КОД [дней]</code> — выдать Premium (по умолчанию год)\n"
                 "<code>/ungrant КОД</code> — забрать\n<code>/users</code> — последние пользователи\n"
                 "<code>/stats</code> — цифры", MENU)
        return
    if "successful_payment" in m:
        uid = user_by_tg(chat)
        if uid:
            until = grant_premium(uid)
            send(token, chat,
                 f"✅ <b>Оплата прошла!</b>\n\n💫 Premium активен до <b>{until}</b>.\n"
                 f"Открой приложение и нажми «Обновить статус» — функции уже разблокированы 💞",
                 MENU)
            try:
                bonus = reward_referrer(chat)
                if bonus:
                    rtg, runtil = bonus
                    if rtg:
                        send(token, rtg,
                             f"🎉 <b>По твоей ссылке купили Premium!</b>\n"
                             f"Тебе +{REF_BONUS} дней — теперь до <b>{runtil}</b> 💫",
                             MENU)
            except Exception:
                pass
        else:
            send(token, chat,
                 "Оплата прошла, но аккаунт не привязан. Пришли код из приложения "
                 "(Ещё → Premium → «Показать код»).", MENU)
        return
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].startswith("ref_"):
            try:
                who = int(parts[1][4:])
            except ValueError:
                who = -1
            res = record_ref(chat, who) if who > 0 else "nouser"
            send(token, chat,
                 "🎉 <b>Ты пришёл по приглашению!</b> Когда купишь Premium — "
                 "друг получит бонусные дни 💫\n\n"
                 "Теперь привяжи свой аккаунт: возьми код в приложении "
                 "(<b>Ещё → Premium → «Показать код»</b>) и пришли его сюда."
                 if res == "ok" else
                 "Привязка не удалась, но ты всё равно можешь пользоваться ботом: "
                 "пришли код из приложения (<b>Ещё → Premium</b>).",
                 MENU)
        elif len(parts) > 1:
            ok, msg, _ = link_code(chat, tg_name, parts[1])
            send(token, chat, msg if ok else "❌ " + msg, MENU)
        else:
            uid = user_by_tg(chat)
            if not uid:
                send_welcome(token, chat)
            send(token, chat,
                 ("✅ <b>Ты уже привязан.</b> Нажми «Купить Premium 💫» — и всё твоё."
                  if uid else
                  "<b>Привет! Это бот подписки Enrwine 💞</b>\n\n"
                  "1️⃣ Возьми код в приложении: <b>Ещё → Premium → «Показать код»</b>\n"
                  "2️⃣ Пришли код сюда (или перейди по кнопке «Открыть бота» — код подставится сам)\n"
                  "3️⃣ Нажми «Купить Premium 💫» и перейди к оплате"),
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
    if text == "Пригласить друга 💌":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                 "Сначала привяжи аккаунт: пришли код из приложения (<b>Ещё → Premium</b>).",
                 MENU)
            return
        inv, earn = ref_stats(uid)
        send(token, chat,
             f"💌 <b>Твоя ссылка:</b>\n<code>{ref_link(uid)}</code>\n\n"
             f"Друг ставит приложение, привязывается и покупает Premium — "
             f"тебе <b>+{REF_BONUS} дней</b> за каждого 🎁\n"
             f"Пришло: {inv} • Купили: {earn} • Заработано дней: {earn * REF_BONUS}",
             MENU)
        return
    if text == "Купить Premium 💫":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                 "Сначала привяжи аккаунт: пришли код из приложения (<b>Ещё → Premium</b>).",
                 MENU)
            return
        send_payment(token, chat, uid)
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
