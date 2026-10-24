"""Telegram-бот подписки Enrwine: привязка по email + оплата.

Запуск: импортируется из main.py (threading в startup) при заданном
TELEGRAM_BOT_TOKEN. Только стандартная библиотека, зависимостей нет.

Переменные окружения:
  TELEGRAM_BOT_TOKEN — токен от @BotFather (обязательно для запуска)
  TELEGRAM_BOT_NAME  — username бота без @ (для ссылок, по умолчанию Enrwine_bot)
  PREMIUM_DAYS       — дней Premium за оплату (по умолчанию 31)
  PREMIUM_PRICE      — цена Premium для сообщений бота (по умолчанию 349 ₽)
  PREMIUM_STARS      — цена Premium в Telegram Stars (по умолчанию 249)
  PAYMENT_URL        — ссылка на оплату в банке
  COUPLE_DB          — путь к базе (как у main.py)
"""
import datetime
import json
import logging
import os
import re
import socket
import sqlite3
import time

import requests

try:
    from backend.time_utils import utc_iso, utc_today
except ImportError:
    from time_utils import utc_iso, utc_today

# На части VDS нет IPv6, а резолвер может отдавать Telegram только по AAAA.
# Принудительно ходим по IPv4, чтобы long polling не падал с EHOSTUNREACH.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(*args, **kwargs):
    kwargs.pop("family", None)
    infos = _orig_getaddrinfo(*args, **kwargs)
    v4 = [i for i in infos if i[0] == socket.AF_INET]
    return v4 + [i for i in infos if i[0] != socket.AF_INET]


socket.getaddrinfo = _ipv4_first_getaddrinfo

API = "https://api.telegram.org/bot"
HTTP = requests.Session() if hasattr(requests, "Session") else requests
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("COUPLE_DB", os.path.join(BASE_DIR, "couple.db"))
BOT_NAME = os.environ.get("TELEGRAM_BOT_NAME", "Enrwine_bot")
PREMIUM_DAYS = int(os.environ.get("PREMIUM_DAYS", "31"))
PREMIUM_PRICE = os.environ.get("PREMIUM_PRICE", "349 ₽")
PREMIUM_STARS = int(os.environ.get("PREMIUM_STARS", "249"))
PREMIUM_PLANS = {
    "1": {"months": 1, "days": PREMIUM_DAYS, "stars": PREMIUM_STARS,
          "price": PREMIUM_PRICE},
    "3": {"months": 3, "days": 93, "stars": 699, "price": "949 ₽"},
    "6": {"months": 6, "days": 186, "stars": 1199, "price": "1799 ₽"},
}
PAYMENT_URL = os.environ.get(
    "PAYMENT_URL",
    "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79333335415&bankCode=100000000111",
)
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_TG_IDS", "").split(",") if x.strip().isdigit()}
REF_BONUS = int(os.environ.get("REF_BONUS_DAYS", "7"))
APP_URL = os.environ.get("APP_PUBLIC_URL", "https://153-76-163-41.sslip.io")
ICON_URL = APP_URL.rstrip("/") + "/icons/icon-512.png"
APK_URL = os.environ.get("ANDROID_APK_URL", APP_URL.rstrip("/") + "/Enrwine.apk")
TELEGRAM_PROXY = os.environ.get("TELEGRAM_PROXY", "")

_STATUS = {
    "running": False,
    "healthy": False,
    "last_poll": None,
    "last_error": None,
}
_PENDING_INPUT = {}


def bot_status():
    return dict(_STATUS)


def _record_error(exc):
    message = f"{type(exc).__name__}: {exc}"
    message = re.sub(r"/bot[^/\s]+/", "/bot<redacted>/", message)[:300]
    if message != _STATUS["last_error"]:
        logging.warning("Telegram bot polling failed: %s", message)
    _STATUS["healthy"] = False
    _STATUS["last_error"] = message


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def api(token, method, payload=None, timeout=20):
    url = API + token + "/" + method
    proxies = {"https": TELEGRAM_PROXY} if TELEGRAM_PROXY else None
    response = HTTP.post(url, json=payload, proxies=proxies, timeout=timeout)
    response.raise_for_status()
    return response.json()


def send(token, chat, text, buttons=None):
    if buttons == MENU and chat in ADMIN_IDS:
        buttons = ADMIN_MENU
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


def send_card_payment(token, chat, uid, plan_key="1"):
    plan = PREMIUM_PLANS[plan_key]
    con = db()
    user = con.execute("SELECT email FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    email = safe(user["email"]) if user and user["email"] else "не указана"
    payload = {
        "chat_id": chat,
        "text": (f"💫 <b>Enrwine Premium — {plan['price']} за "
                 f"{plan['months']} мес.</b>\n\n"
                 "Нажми кнопку ниже для оплаты через СберБанк. "
                 "После оплаты отправь чек администратору для активации Premium.\n\n"
                 f"Почта аккаунта: <code>{email}</code>"),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{
                "text": f"Оплатить {plan['price']}",
                "url": PAYMENT_URL,
            }]],
        },
    }
    try:
        api(token, "sendMessage", payload)
    except Exception:
        send(token, chat, f"Ссылка для оплаты:\n{PAYMENT_URL}", MENU)


def stars_payload(uid, plan_key="1"):
    plan = PREMIUM_PLANS[plan_key]
    return f"premium:{uid}:{plan['days']}:{plan['stars']}"


def send_stars_payment(token, chat, uid, plan_key="1"):
    plan = PREMIUM_PLANS[plan_key]
    api(token, "sendInvoice", {
        "chat_id": chat,
        "title": "Enrwine Premium",
        "description": (f"Premium для вашей пары на {plan['months']} мес. "
                         "Доступ откроется автоматически после оплаты."),
        "payload": stars_payload(uid, plan_key),
        "currency": "XTR",
        "prices": [{"label": f"Premium на {plan['months']} мес.",
                    "amount": plan["stars"]}],
    })


def send_plan_picker(token, chat):
    rows = []
    for key, plan in PREMIUM_PLANS.items():
        rows.append([
            {"text": f"{key} мес. · {plan['stars']} ⭐",
             "callback_data": f"premium:stars:{key}"},
            {"text": plan["price"], "callback_data": f"premium:card:{key}"},
        ])
    api(token, "sendMessage", {
        "chat_id": chat,
        "text": ("<b>Выбери срок Premium 💫</b>\n\n"
                 "Слева — оплата Telegram Stars, справа — банковской картой."),
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": rows},
    })


def safe(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_welcome(token, chat):
    try:
        api(token, "sendPhoto", {
            "chat_id": chat, "photo": ICON_URL,
            "caption": (
                "<b>Добро пожаловать в Enrwine 💞</b>\n\n"
                "Это личное пространство для двоих: вопросы дня, общая карта, "
                "воспоминания, игры и другие способы быть ближе.\n\n"
                "Установи приложение, зарегистрируйся, "
                "а затем вернись сюда и пришли почту своего аккаунта."
            ),
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": [
                [{"text": "Скачать на Android 📲", "url": APK_URL}],
            ]},
        })
    except Exception:
        pass


def send_download(token, chat):
    send_payload = {
        "chat_id": chat,
        "text": (
            "<b>Скачать Enrwine</b>\n\n"
            "Для Android скачай APK и разреши установку из браузера, если телефон "
            "попросит подтверждение."
        ),
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [
            [{"text": "Скачать APK для Android 📲", "url": APK_URL}],
        ]},
    }
    try:
        api(token, "sendMessage", send_payload)
    except Exception:
        send(token, chat, f"Скачать приложение:\n{APK_URL}", MENU)


def grant_premium(user_id, days=PREMIUM_DAYS):
    con = db()
    row = con.execute("SELECT premium_until FROM users WHERE id=?",
                      (user_id,)).fetchone()
    try:
        cur = datetime.date.fromisoformat(row["premium_until"])
    except (ValueError, TypeError):
        cur = None
    start = max(utc_today(), cur) if cur else utc_today()
    until = (start + datetime.timedelta(days=days)).isoformat()
    con.execute("UPDATE users SET premium_until=? WHERE id=?",
                (until, user_id))
    con.commit()
    con.close()
    return until


def link_email(tg_id, tg_name, email):
    """Привязка Telegram к аккаунту по почте входа."""
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return False, "Пришли почту, с которой входишь в Enrwine.", None
    con = db()
    user = con.execute("SELECT id, name FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        con.close()
        return False, "Аккаунт с такой почтой не найден. Проверь адрес и отправь ещё раз.", None
    uid = user["id"]
    now = utc_iso()
    con.execute("DELETE FROM tg WHERE tg_id=? AND user_id!=?", (tg_id, uid))
    con.execute(
        "INSERT INTO tg(user_id,tg_id,tg_name,ts) VALUES(?,?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET tg_id=excluded.tg_id, "
        "tg_name=excluded.tg_name, ts=excluded.ts",
        (uid, tg_id, tg_name, now))
    con.commit()
    con.close()
    telegram_name = safe(tg_name) if tg_name else f"Telegram ID {tg_id}"
    return True, (f"✅ <b>Готово!</b> Почта <code>{safe(email)}</code> привязана "
                  f"к Telegram-аккаунту <b>{telegram_name}</b>.\n"
                  "Нажми «Купить Premium 💫» для оплаты"), uid


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


MENU = [["Купить Premium 💫"],
        ["Мой статус ⭐", "Пригласить друга 💌"],
        ["Скачать приложение 📲"]]
ADMIN_MENU = MENU + [["Ожидают выплаты 💳", "Выплаченные заявки ✅"]]


def validate_stars_payment(tg_id, payment):
    uid = user_by_tg(tg_id)
    if not uid:
        return None
    if payment.get("currency") != "XTR":
        return None
    for key, plan in PREMIUM_PLANS.items():
        if (payment.get("total_amount") == plan["stars"] and
                payment.get("invoice_payload") == stars_payload(uid, key)):
            return uid
    return None


def payment_plan(uid, payment):
    for key, plan in PREMIUM_PLANS.items():
        if (payment.get("total_amount") == plan["stars"] and
                payment.get("invoice_payload") == stars_payload(uid, key)):
            return plan
    return None


def activate_stars_payment(tg_id, payment):
    """Активирует подтверждённый Telegram-платёж ровно один раз."""
    uid = validate_stars_payment(tg_id, payment)
    plan = payment_plan(uid, payment) if uid is not None else None
    charge_id = payment.get("telegram_payment_charge_id") or ""
    if uid is None or plan is None or not charge_id:
        return None, False
    con = db()
    now = utc_iso()
    inserted = con.execute(
        "INSERT OR IGNORE INTO tg_payments("
        "charge_id,provider_charge_id,user_id,tg_id,currency,total_amount,payload,ts) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (charge_id, payment.get("provider_payment_charge_id") or "", uid, tg_id,
         "XTR", plan["stars"], payment["invoice_payload"], now),
    ).rowcount
    row = con.execute("SELECT premium_until FROM users WHERE id=?", (uid,)).fetchone()
    if not inserted:
        con.close()
        return (row["premium_until"] if row else ""), False
    try:
        current = datetime.date.fromisoformat(row["premium_until"])
    except (ValueError, TypeError):
        current = None
    start = max(utc_today(), current) if current else utc_today()
    until = (start + datetime.timedelta(days=plan["days"])).isoformat()
    con.execute("UPDATE users SET premium_until=? WHERE id=?", (until, uid))
    con.commit()
    con.close()
    return until, True


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
    now = utc_iso()
    con.execute("INSERT INTO refs(tg_id,referrer,ts) VALUES(?,?,?)",
                (tg_id, referrer_uid, now))
    con.commit()
    con.close()
    return "ok"


def create_referral_reward(payer_tg_id, payer_uid):
    """Создаёт одну награду после первой оплаты приглашённого пользователя."""
    con = db()
    r = con.execute("SELECT referrer FROM refs WHERE tg_id=? AND rewarded=0",
                    (payer_tg_id,)).fetchone()
    if not r:
        con.close()
        return None
    now = utc_iso()
    inserted = con.execute(
        "INSERT OR IGNORE INTO referral_rewards("
        "referred_tg_id,referrer_user_id,referred_user_id,created_at) "
        "VALUES(?,?,?,?)",
        (payer_tg_id, r["referrer"], payer_uid, now),
    ).rowcount
    con.execute("UPDATE refs SET rewarded=1 WHERE tg_id=?", (payer_tg_id,))
    rt = con.execute("SELECT tg_id FROM tg WHERE user_id=?", (r["referrer"],)).fetchone()
    reward = con.execute(
        "SELECT id FROM referral_rewards WHERE referred_tg_id=?", (payer_tg_id,)
    ).fetchone()
    con.commit()
    con.close()
    if not inserted or not reward:
        return None
    return {
        "id": reward["id"],
        "referrer_user_id": r["referrer"],
        "tg_id": rt["tg_id"] if rt and rt["tg_id"] else None,
    }


def choose_referral_reward(user_id, reward_id, choice):
    if choice not in ("cash", "premium"):
        return None
    con = db()
    con.execute("BEGIN IMMEDIATE")
    reward = con.execute(
        "SELECT * FROM referral_rewards WHERE id=? AND referrer_user_id=?",
        (reward_id, user_id),
    ).fetchone()
    if not reward or reward["status"] != "awaiting_choice":
        con.close()
        return None
    now = utc_iso()
    if choice == "cash":
        con.execute(
            "UPDATE referral_rewards SET choice='cash',status='available',chosen_at=? "
            "WHERE id=?", (now, reward_id)
        )
        result = {"choice": "cash", "amount": reward["amount_rub"]}
    else:
        row = con.execute(
            "SELECT premium_until FROM users WHERE id=?", (user_id,)
        ).fetchone()
        try:
            current = datetime.date.fromisoformat(row["premium_until"])
        except (ValueError, TypeError):
            current = None
        start = max(utc_today(), current) if current else utc_today()
        until = (start + datetime.timedelta(days=reward["bonus_days"])).isoformat()
        con.execute("UPDATE users SET premium_until=? WHERE id=?", (until, user_id))
        con.execute(
            "UPDATE referral_rewards SET choice='premium',status='applied',chosen_at=? "
            "WHERE id=?", (now, reward_id)
        )
        result = {"choice": "premium", "until": until}
    con.commit()
    con.close()
    return result


def choose_referral_rewards(user_id, choice, count):
    if choice not in ("cash", "premium") or count < 1:
        return None, "Укажи целое число от 1."
    con = db()
    con.execute("BEGIN IMMEDIATE")
    rewards = con.execute(
        "SELECT * FROM referral_rewards "
        "WHERE referrer_user_id=? AND status='awaiting_choice' "
        "ORDER BY id LIMIT ?",
        (user_id, count),
    ).fetchall()
    if len(rewards) != count:
        available = con.execute(
            "SELECT COUNT(*) n FROM referral_rewards "
            "WHERE referrer_user_id=? AND status='awaiting_choice'",
            (user_id,),
        ).fetchone()["n"]
        con.close()
        return None, f"Можно выбрать от 1 до {available}."
    now = utc_iso()
    ids = [reward["id"] for reward in rewards]
    placeholders = ",".join("?" for _ in ids)
    if choice == "cash":
        con.execute(
            f"UPDATE referral_rewards SET choice='cash',status='available',chosen_at=? "
            f"WHERE id IN ({placeholders})",
            (now, *ids),
        )
        result = {"choice": "cash", "count": count,
                  "amount": sum(reward["amount_rub"] for reward in rewards)}
    else:
        row = con.execute(
            "SELECT premium_until FROM users WHERE id=?", (user_id,)
        ).fetchone()
        try:
            current = datetime.date.fromisoformat(row["premium_until"])
        except (ValueError, TypeError):
            current = None
        days = sum(reward["bonus_days"] for reward in rewards)
        start = max(utc_today(), current) if current else utc_today()
        until = (start + datetime.timedelta(days=days)).isoformat()
        con.execute("UPDATE users SET premium_until=? WHERE id=?", (until, user_id))
        con.execute(
            f"UPDATE referral_rewards SET choice='premium',status='applied',chosen_at=? "
            f"WHERE id IN ({placeholders})",
            (now, *ids),
        )
        result = {"choice": "premium", "count": count,
                  "days": days, "until": until}
    con.commit()
    con.close()
    return result, None


def ref_stats(uid):
    con = db()
    inv = con.execute("SELECT COUNT(*) n FROM refs WHERE referrer=?", (uid,)).fetchone()["n"]
    earn = con.execute("SELECT COUNT(*) n FROM refs WHERE referrer=? AND rewarded=1",
                       (uid,)).fetchone()["n"]
    rewards = con.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN status='awaiting_choice' THEN 1 ELSE 0 END),0) choosing,"
        "COALESCE(SUM(CASE WHEN status='available' THEN amount_rub ELSE 0 END),0) available,"
        "COALESCE(SUM(CASE WHEN status='requested' THEN amount_rub ELSE 0 END),0) requested,"
        "COALESCE(SUM(CASE WHEN status='paid' THEN amount_rub ELSE 0 END),0) paid "
        "FROM referral_rewards WHERE referrer_user_id=?", (uid,)
    ).fetchone()
    con.close()
    return {
        "invited": inv,
        "converted": earn,
        "choosing": rewards["choosing"],
        "available": rewards["available"],
        "requested": rewards["requested"],
        "paid": rewards["paid"],
    }


def create_referral_payout(user_id, recipient):
    recipient = " ".join((recipient or "").strip().split())
    if len(recipient) < 8 or not any(char.isdigit() for char in recipient):
        return None, "Укажи номер телефона и банк, например: <code>+79991234567 · Сбербанк</code>"
    con = db()
    con.execute("BEGIN IMMEDIATE")
    rewards = con.execute(
        "SELECT id,amount_rub FROM referral_rewards "
        "WHERE referrer_user_id=? AND status='available' ORDER BY id",
        (user_id,),
    ).fetchall()
    if not rewards:
        con.close()
        return None, "Сейчас нет доступных денежных наград."
    amount = sum(row["amount_rub"] for row in rewards)
    now = utc_iso()
    cursor = con.execute(
        "INSERT INTO referral_payouts(user_id,amount_rub,recipient,created_at) "
        "VALUES(?,?,?,?)", (user_id, amount, recipient, now)
    )
    payout_id = cursor.lastrowid
    con.executemany(
        "UPDATE referral_rewards SET status='requested',payout_id=? WHERE id=?",
        [(payout_id, row["id"]) for row in rewards],
    )
    con.commit()
    con.close()
    return {"id": payout_id, "amount": amount, "recipient": recipient}, None


def send_referral_reward_choice(token, chat, reward_id):
    api(token, "sendMessage", {
        "chat_id": chat,
        "text": ("🎉 <b>По твоей ссылке впервые купили Premium!</b>\n\n"
                 "Открой реферальную программу и выбери, сколько наград "
                 "обменять на деньги или дни Premium."),
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[
            {"text": "Получить деньги", "callback_data": "ref_reward:cash:start"},
            {"text": "Получить дни", "callback_data": "ref_reward:premium:start"},
        ]]},
    })


def send_referral_dashboard(token, chat, uid):
    stats = ref_stats(uid)
    text = (
        f"💌 <b>Реферальная программа</b>\n\n"
        f"Твоя ссылка:\n<code>{ref_link(uid)}</code>\n\n"
        f"Приглашено: <b>{stats['invited']}</b>\n"
        f"Купили Premium: <b>{stats['converted']}</b>\n"
        f"Ждут выбора награды: <b>{stats['choosing']}</b>\n\n"
        f"Доступно к выплате: <b>{stats['available']} ₽</b>\n"
        f"В обработке: <b>{stats['requested']} ₽</b>\n"
        f"Выплачено: <b>{stats['paid']} ₽</b>\n\n"
        "За первую покупку каждого приглашённого можно выбрать 100 ₽ или "
        f"+{REF_BONUS} дней Premium. Твой Premium для участия не требуется."
    )
    buttons = []
    if stats["choosing"]:
        buttons.append([
            {"text": f"Деньги · до {stats['choosing'] * 100} ₽",
             "callback_data": "ref_reward:cash:start"},
            {"text": f"Premium · до +{stats['choosing'] * REF_BONUS} дней",
             "callback_data": "ref_reward:premium:start"},
        ])
    if stats["available"]:
        buttons.append([{
            "text": f"Запросить выплату {stats['available']} ₽",
            "callback_data": "ref_payout:start",
        }])
    api(token, "sendMessage", {
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        **({"reply_markup": {"inline_keyboard": buttons}} if buttons else {}),
    })


def submit_referral_payout(token, chat, uid, recipient):
    payout, error = create_referral_payout(uid, recipient)
    if error:
        send(token, chat, error, MENU)
        return False
    send(token, chat,
         f"✅ <b>Заявка #{payout['id']} создана</b>\n\n"
         f"Сумма: <b>{payout['amount']} ₽</b>\n"
         f"Реквизиты: <code>{safe(payout['recipient'])}</code>\n\n"
         "После ручного перевода бот пришлёт подтверждение.", MENU)
    con = db()
    user = con.execute("SELECT name,email FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    notify_admins(
        token,
        f"💳 <b>Новая заявка на реферальную выплату</b>\n"
        f"Заявка: <b>#{payout['id']}</b> · <b>{payout['amount']} ₽</b>\n"
        f"Пользователь: {safe(user['name'] if user else str(uid))}\n"
        f"Email: <code>{safe(user['email'] if user else '')}</code>\n"
        f"Реквизиты: <code>{safe(payout['recipient'])}</code>\n\n"
        f"После перевода: <code>/pay {payout['id']}</code>",
    )
    return True


def admin_payouts(status="pending"):
    if status not in ("pending", "paid", "rejected", "all"):
        status = "pending"
    con = db()
    where = "" if status == "all" else "WHERE p.status=?"
    args = () if status == "all" else (status,)
    rows = con.execute(
        "SELECT p.*,u.name,u.email,t.tg_name FROM referral_payouts p "
        "LEFT JOIN users u ON u.id=p.user_id LEFT JOIN tg t ON t.user_id=p.user_id "
        f"{where} ORDER BY p.id DESC LIMIT 30", args
    ).fetchall()
    totals = con.execute(
        "SELECT status,COUNT(*) n,COALESCE(SUM(amount_rub),0) amount "
        "FROM referral_payouts GROUP BY status"
    ).fetchall()
    con.close()
    summary = " · ".join(f"{r['status']}: {r['n']} / {r['amount']} ₽" for r in totals)
    lines = [f"💳 <b>Реферальные выплаты</b> ({status})", summary or "Заявок пока нет."]
    for row in rows:
        name = safe(row["name"] or row["tg_name"] or f"id {row['user_id']}")
        action = (f"\nПосле перевода: <code>/pay {row['id']}</code>"
                  if row["status"] == "pending" else
                  f"\nВыплачено: {row['paid_at']}" if row["status"] == "paid" else "")
        lines.append(
            f"\n<b>#{row['id']} · {row['amount_rub']} ₽ · {row['status']}</b>\n"
            f"{name} · <code>{safe(row['email'] or '')}</code>\n"
            f"<code>{safe(row['recipient'])}</code>\n{row['created_at']}{action}"
        )
    return "\n".join(lines)


def admin_finish_payout(payout_id, paid=True, note=""):
    con = db()
    con.execute("BEGIN IMMEDIATE")
    payout = con.execute(
        "SELECT * FROM referral_payouts WHERE id=?", (payout_id,)
    ).fetchone()
    if not payout or payout["status"] != "pending":
        con.close()
        return None
    now = utc_iso()
    status = "paid" if paid else "rejected"
    con.execute(
        "UPDATE referral_payouts SET status=?,paid_at=?,admin_note=? WHERE id=?",
        (status, now if paid else "", note, payout_id),
    )
    con.execute(
        "UPDATE referral_rewards SET status=? WHERE payout_id=? AND status='requested'",
        ("paid" if paid else "available", payout_id),
    )
    tg = con.execute("SELECT tg_id FROM tg WHERE user_id=?", (payout["user_id"],)).fetchone()
    con.commit()
    con.close()
    return {
        "id": payout_id,
        "amount": payout["amount_rub"],
        "recipient": payout["recipient"],
        "tg_id": tg["tg_id"] if tg else None,
        "status": status,
    }


def is_admin(tg_id):
    return tg_id in ADMIN_IDS


def notify_admins(token, text):
    for admin_id in ADMIN_IDS:
        send(token, admin_id, text, MENU)


def find_user(key):
    """Поиск пользователя по id или email. Возвращает (id, name) или None."""
    key = (key or "").strip()
    con = db()
    row = None
    if key.isdigit():
        row = con.execute("SELECT id, name FROM users WHERE id=?",
                          (int(key),)).fetchone()
    if row is None and key:
        row = con.execute("SELECT id, name FROM users WHERE email=?",
                          (key.lower(),)).fetchone()
    con.close()
    return (row["id"], row["name"]) if row else None


def admin_grant(key, days):
    found = find_user(key)
    if not found:
        return "Пользователь не найден. Пришли email или id."
    uid, name = found
    until = grant_premium(uid, days)
    return f"✅ <b>{safe(name)}</b> (id {uid}) — Premium до <b>{until}</b>."


def admin_revoke(key):
    found = find_user(key)
    if not found:
        return "Пользователь не найден. Пришли email или id."
    uid, name = found
    con = db()
    con.execute("UPDATE users SET premium_until='' WHERE id=?", (uid,))
    con.commit()
    con.close()
    return f"Premium у <b>{safe(name)}</b> (id {uid}) выключен."


def admin_users():
    con = db()
    rows = con.execute(
        "SELECT id, name, email, premium_until FROM users ORDER BY id DESC LIMIT 10").fetchall()
    con.close()
    today = utc_today().isoformat()
    lines = []
    for r in rows:
        mark = "💫" if r["premium_until"] and r["premium_until"] >= today else "–"
        account = safe(r["email"]) if r["email"] else f"id {r['id']}"
        lines.append(f"{mark} <b>{safe(r['name'])}</b> ({account})"
                      + (f" до {r['premium_until']}" if r["premium_until"] else ""))
    return "Последние пользователи:\n" + "\n".join(lines) if lines else "Пока пусто."


def admin_user(key):
    found = find_user(key)
    if not found:
        return "Пользователь не найден. Пришли email или id."
    uid, _ = found
    con = db()
    user = con.execute(
        "SELECT id,name,email,partner_id,premium_until FROM users WHERE id=?", (uid,)
    ).fetchone()
    partner = con.execute(
        "SELECT id,name,premium_until FROM users WHERE id=?", (user["partner_id"],)
    ).fetchone() if user["partner_id"] else None
    telegram = con.execute("SELECT tg_id,tg_name FROM tg WHERE user_id=?", (uid,)).fetchone()
    payments = con.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(total_amount),0) stars "
        "FROM tg_payments WHERE user_id=?", (uid,)
    ).fetchone()
    con.close()
    untils = [x for x in (
        user["premium_until"], partner["premium_until"] if partner else ""
    ) if x and x >= utc_today().isoformat()]
    pair_until = max(untils, default="не активен")
    account = safe(user["email"]) if user["email"] else "не указана"
    partner_text = (f"{safe(partner['name'])} (id {partner['id']})"
                    if partner else "нет")
    tg_text = (f"{telegram['tg_id']} {safe(telegram['tg_name'])}"
               if telegram else "не привязан")
    return (f"👤 <b>{safe(user['name'])}</b> · id <code>{uid}</code>\n"
            f"Email: <code>{account}</code>\n"
            f"Telegram: {tg_text}\n"
            f"Партнёр: {partner_text}\n"
            f"Premium пользователя: {user['premium_until'] or 'нет'}\n"
            f"Premium пары: <b>{pair_until}</b>\n"
            f"Stars-платежей: {payments['n']} на {payments['stars']} ⭐")


def admin_subscribers():
    con = db()
    today = utc_today().isoformat()
    rows = con.execute(
        "SELECT u.id,u.name,u.email,u.premium_until,p.name partner_name "
        "FROM users u LEFT JOIN users p ON p.id=u.partner_id "
        "WHERE u.premium_until>=? ORDER BY u.premium_until DESC", (today,)
    ).fetchall()
    con.close()
    if not rows:
        return "Активных подписок пока нет."
    lines = ["💫 <b>Активные подписки</b>"]
    for r in rows[:30]:
        account = safe(r["email"]) if r["email"] else f"id {r['id']}"
        pair = f" + {safe(r['partner_name'])}" if r["partner_name"] else ""
        lines.append(f"• {safe(r['name'])}{pair} · {account} · до {r['premium_until']}")
    if len(rows) > 30:
        lines.append(f"…и ещё {len(rows) - 30}")
    return "\n".join(lines)


def admin_payments(limit=10):
    limit = max(1, min(int(limit), 30))
    con = db()
    rows = con.execute(
        "SELECT p.*,u.name,u.email FROM tg_payments p "
        "LEFT JOIN users u ON u.id=p.user_id ORDER BY p.ts DESC LIMIT ?", (limit,)
    ).fetchall()
    total = con.execute(
        "SELECT COUNT(*) n,COALESCE(SUM(total_amount),0) stars FROM tg_payments"
    ).fetchone()
    con.close()
    lines = [f"💰 <b>Stars-платежи</b>: {total['n']} на {total['stars']} ⭐"]
    for r in rows:
        name = safe(r["name"]) if r["name"] else f"id {r['user_id']}"
        lines.append(f"• {r['total_amount']} ⭐ · {name} · {r['ts']}\n"
                     f"  <code>{safe(r['charge_id'])}</code>")
    if not rows:
        lines.append("Платежей пока нет.")
    return "\n".join(lines)


def admin_stats():
    con = db()
    users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    today = utc_today().isoformat()
    rows = con.execute("SELECT id,partner_id,premium_until FROM users").fetchall()
    premium_owners = {r["id"] for r in rows
                      if r["premium_until"] and r["premium_until"] >= today}
    premium_access = set(premium_owners)
    for r in rows:
        if r["id"] in premium_owners and r["partner_id"]:
            premium_access.add(r["partner_id"])
    pairs = sum(1 for r in rows if r["partner_id"] and r["id"] < r["partner_id"])
    linked = con.execute("SELECT COUNT(*) n FROM tg").fetchone()["n"]
    payments = con.execute(
        "SELECT COUNT(*) n,COALESCE(SUM(total_amount),0) stars FROM tg_payments"
    ).fetchone()
    referrals = con.execute(
        "SELECT COUNT(*) invited,COALESCE(SUM(rewarded),0) paid FROM refs"
    ).fetchone()
    payouts = con.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN status='pending' THEN amount_rub ELSE 0 END),0) pending,"
        "COALESCE(SUM(CASE WHEN status='paid' THEN amount_rub ELSE 0 END),0) paid "
        "FROM referral_payouts"
    ).fetchone()
    sharing = con.execute("SELECT COUNT(*) n FROM locations").fetchone()["n"]
    con.close()
    return (f"📊 <b>Статистика Enrwine</b>\n"
            f"Пользователей: {users}\nПар: {pairs}\nTelegram привязан: {linked}\n"
            f"Оплатили Premium: {len(premium_owners)}\n"
            f"Имеют доступ с учётом пары: {len(premium_access)}\n"
            f"Stars-платежей: {payments['n']} на {payments['stars']} ⭐\n"
            f"Рефералов: {referrals['invited']} · оплатили: {referrals['paid']}\n"
            f"Реферальные выплаты: ожидают {payouts['pending']} ₽ · выплачено {payouts['paid']} ₽\n"
            f"Делятся геопозицией: {sharing}")


def admin_help():
    return ("🔧 <b>Админка Enrwine</b>\n"
            "<code>/stats</code> — общая статистика\n"
             "<code>/payments [1-30]</code> — последние Stars-платежи\n"
             "<code>/payouts [pending|paid|all]</code> — реферальные выплаты\n"
             "<code>/pay id</code> — отметить выплату отправленной\n"
             "<code>/payout_reject id причина</code> — вернуть сумму на баланс\n"
            "<code>/subscribers</code> — активные подписки\n"
            "<code>/users</code> — последние пользователи\n"
            "<code>/user email|id</code> — карточка пользователя\n"
            "<code>/grant email|id [дней]</code> — выдать Premium\n"
            "<code>/ungrant email|id</code> — отключить Premium\n"
            "<code>/myid</code> — показать ваш Telegram ID")


def handle_message(token, m):
    chat = m["chat"]["id"]
    sender = m.get("from") or m["chat"]
    username = (sender.get("username") or m["chat"].get("username") or "").strip()
    first_name = (sender.get("first_name") or m["chat"].get("first_name") or "").strip()
    tg_name = f"@{username}" if username else first_name
    text = (m.get("text") or "").strip()
    reply_text = ((m.get("reply_to_message") or {}).get("text") or "")
    pending_input = _PENDING_INPUT.get(chat, "")
    menu_texts = {item for row in ADMIN_MENU for item in row}
    if pending_input and (text.startswith("/") or text in menu_texts):
        _PENDING_INPUT.pop(chat, None)
        pending_input = ""
    reward_choice = (
        "cash" if pending_input == "reward:cash" or
        "КОЛИЧЕСТВО ДЛЯ ДЕНЕГ" in reply_text else
        "premium" if pending_input == "reward:premium" or
        "КОЛИЧЕСТВО ДЛЯ PREMIUM" in reply_text else None
    )
    if reward_choice:
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat, "Сначала привяжи аккаунт Enrwine.", MENU)
            return
        if not text.isdigit() or int(text) < 1:
            send(token, chat, "Укажи целое число рефералов, например: <code>3</code>", MENU)
            return
        result, error = choose_referral_rewards(uid, reward_choice, int(text))
        if error:
            send(token, chat, error, MENU)
            return
        _PENDING_INPUT.pop(chat, None)
        if result["choice"] == "cash":
            send(token, chat,
                 f"✅ Награды за <b>{result['count']}</b> рефералов обменены на "
                 f"<b>{result['amount']} ₽</b>.", MENU)
        else:
            send(token, chat,
                 f"✅ За <b>{result['count']}</b> рефералов начислено "
                 f"<b>+{result['days']} дней Premium</b>.\n"
                 f"Premium активен до <b>{result['until']}</b>.", MENU)
        send_referral_dashboard(token, chat, uid)
        return
    if (pending_input == "payout" or text == "/payout" or text.startswith("/payout ") or
            "РЕКВИЗИТЫ ВЫПЛАТЫ" in reply_text):
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat, "Сначала привяжи аккаунт Enrwine.", MENU)
            return
        recipient = text.partition(" ")[2] if text.startswith("/payout") else text
        if submit_referral_payout(token, chat, uid, recipient):
            _PENDING_INPUT.pop(chat, None)
        return
    if text == "/myid":
        send(token, chat, f"Ваш Telegram ID: <code>{chat}</code>", MENU)
        return
    command = text.split(maxsplit=1)[0] if text.startswith("/") else ""
    if command in ("/grant", "/ungrant", "/users", "/stats", "/admin",
                   "/payments", "/payouts", "/pay", "/payout_reject",
                   "/subscribers", "/user"):
        if not is_admin(chat):
            send(token, chat, "Нет доступа 🔒", MENU)
            return
        parts = text.split()
        cmd = parts[0]
        if cmd == "/grant":
            days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 365
            key = parts[1] if len(parts) > 1 else ""
            send(token, chat, admin_grant(key, days) if key else
                  "Формат: <code>/grant email [дней]</code>\nПример: <code>/grant user@mail.ru 365</code>",
                 MENU)
        elif cmd == "/ungrant":
            key = parts[1] if len(parts) > 1 else ""
            send(token, chat, admin_revoke(key) if key else
                  "Формат: <code>/ungrant email</code>", MENU)
        elif cmd == "/users":
            send(token, chat, admin_users(), MENU)
        elif cmd == "/stats":
            send(token, chat, admin_stats(), MENU)
        elif cmd == "/payments":
            limit = parts[1] if len(parts) > 1 and parts[1].isdigit() else 10
            send(token, chat, admin_payments(limit), MENU)
        elif cmd == "/payouts":
            send(token, chat, admin_payouts(parts[1] if len(parts) > 1 else "pending"), MENU)
        elif cmd in ("/pay", "/payout_reject"):
            payout_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            note = " ".join(parts[2:])
            result = admin_finish_payout(payout_id, cmd == "/pay", note) if payout_id else None
            if not result:
                send(token, chat, "Заявка не найдена или уже обработана.", MENU)
            else:
                action = "выплачена" if result["status"] == "paid" else "отклонена"
                send(token, chat,
                     f"✅ Заявка #{result['id']} {action}: {result['amount']} ₽\n"
                     f"<code>{safe(result['recipient'])}</code>", MENU)
                if result["tg_id"]:
                    send(token, result["tg_id"],
                         (f"✅ <b>Выплата {result['amount']} ₽ отправлена</b>"
                          if result["status"] == "paid" else
                          f"Заявка на {result['amount']} ₽ отклонена. Сумма возвращена на баланс."),
                         MENU)
        elif cmd == "/subscribers":
            send(token, chat, admin_subscribers(), MENU)
        elif cmd == "/user":
            key = parts[1] if len(parts) > 1 else ""
            send(token, chat, admin_user(key) if key else
                 "Формат: <code>/user email|id</code>", MENU)
        else:
            send(token, chat, admin_help(), MENU)
        return
    if text in ("Ожидают выплаты 💳", "Выплаченные заявки ✅"):
        if not is_admin(chat):
            send(token, chat, "Нет доступа 🔒", MENU)
            return
        status = "pending" if text == "Ожидают выплаты 💳" else "paid"
        send(token, chat, admin_payouts(status), MENU)
        return
    if "successful_payment" in m:
        payment = m["successful_payment"]
        payer_uid = validate_stars_payment(chat, payment)
        until, activated = activate_stars_payment(chat, payment)
        if until:
            send(token, chat,
                 f"✅ <b>{'Оплата прошла!' if activated else 'Платёж уже учтён.'}</b>\n\n"
                 f"💫 Premium активен до <b>{until}</b>.\n"
                 f"Открой приложение и нажми «Обновить статус» — функции уже разблокированы 💞",
                 MENU)
            if activated:
                con = db()
                payer = con.execute(
                    "SELECT name,email FROM users WHERE id=?",
                    (payer_uid,),
                ).fetchone()
                con.close()
                payer_name = safe(payer["name"]) if payer else f"id {payer_uid}"
                payer_email = safe(payer["email"] or "не указан") if payer else "не указан"
                notify_admins(
                    token,
                    f"💰 <b>Новая оплата Premium</b>\n"
                    f"{payment['total_amount']} ⭐ · {payer_name}\n"
                    f"Email: <code>{payer_email}</code>\n"
                    f"User ID: <code>{payer_uid}</code>\n"
                    f"Premium до: <b>{until}</b>\n"
                    f"Charge: <code>{safe(payment['telegram_payment_charge_id'])}</code>",
                )
                try:
                    reward = create_referral_reward(chat, payer_uid)
                    if reward and reward["tg_id"]:
                        send_referral_reward_choice(
                            token, reward["tg_id"], reward["id"]
                        )
                except Exception:
                    pass
        else:
            send(token, chat,
                 "Не удалось проверить платёж. Деньги не должны быть списаны. "
                 "Если списание произошло, напиши администратору.", MENU)
        return
    if text.startswith("/start"):
        send_welcome(token, chat)
        parts = text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].startswith("ref_"):
            try:
                who = int(parts[1][4:])
            except ValueError:
                who = -1
            res = record_ref(chat, who) if who > 0 else "nouser"
            send(token, chat,
                 "🎉 <b>Ты пришёл по приглашению!</b> Когда купишь Premium — "
                 "друг сможет выбрать 100 ₽ или бонусные дни 💫\n\n"
                  "Теперь привяжи свой аккаунт: пришли почту, "
                  "с которой входишь в Enrwine."
                  if res == "ok" else
                  "Привязка не удалась, но ты всё равно можешь пользоваться ботом: "
                  "пришли почту аккаунта Enrwine.",
                  MENU)
        elif len(parts) > 1:
            send(token, chat, "Пришли почту, с которой входишь в Enrwine.", MENU)
        else:
            uid = user_by_tg(chat)
            send(token, chat,
                 ("✅ <b>Ты уже привязан.</b> Нажми «Купить Premium 💫» — и всё твоё."
                  if uid else
                  "<b>Привет! Это бот подписки Enrwine 💞</b>\n\n"
                  "1️⃣ Пришли почту, с которой входишь в Enrwine\n"
                  "2️⃣ Нажми «Купить Premium 💫»\n"
                  "3️⃣ Перейди к оплате"),
                  MENU)
        return
    if text in ("/download", "Скачать приложение 📲"):
        send_download(token, chat)
        return
    if text == "Мой статус ⭐":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                  "Сначала привяжи аккаунт: пришли почту, "
                  "с которой входишь в Enrwine.", MENU)
            return
        until = premium_until(uid) or ""
        try:
            active = bool(until) and datetime.date.fromisoformat(until) >= utc_today()
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
                  "Сначала привяжи аккаунт: пришли почту аккаунта Enrwine.",
                 MENU)
            return
        send_referral_dashboard(token, chat, uid)
        return
    if text == "Купить Premium 💫":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                  "Сначала привяжи аккаунт: пришли почту аккаунта Enrwine.",
                 MENU)
            return
        send_plan_picker(token, chat)
        return
    # Old reply keyboards may remain visible after the bot is updated.
    if text == f"Купить за {PREMIUM_STARS} ⭐":
        uid = user_by_tg(chat)
        if uid:
            send_stars_payment(token, chat, uid)
        else:
            send(token, chat, "Сначала привяжи аккаунт: пришли почту аккаунта Enrwine.", MENU)
        return
    if text == f"Оплатить {PREMIUM_PRICE}":
        uid = user_by_tg(chat)
        if not uid:
            send(token, chat,
                 "Сначала привяжи аккаунт: пришли почту аккаунта Enrwine.",
                 MENU)
            return
        send_card_payment(token, chat, uid)
        return
    # Почта из сообщения связывает Telegram с аккаунтом Enrwine.
    if text:
        ok, msg, _ = link_email(chat, tg_name, text)
        send(token, chat, msg if ok else "❌ " + msg, MENU)


def handle_callback(token, query):
    api(token, "answerCallbackQuery", {"callback_query_id": query["id"]})
    data = query.get("data", "")
    parts = data.split(":")
    chat = query.get("message", {}).get("chat", {}).get("id") or query["from"]["id"]
    uid = user_by_tg(query["from"]["id"])
    if not uid:
        send(token, chat, "Сначала привяжи аккаунт: пришли почту аккаунта Enrwine.", MENU)
        return
    if len(parts) == 3 and parts[0] == "premium" and parts[2] in PREMIUM_PLANS:
        method, plan_key = parts[1], parts[2]
        if method == "stars":
            send_stars_payment(token, chat, uid, plan_key)
        elif method == "card":
            send_card_payment(token, chat, uid, plan_key)
        return
    if len(parts) == 3 and parts[0] == "ref_reward" and parts[2].isdigit():
        result = choose_referral_reward(uid, int(parts[2]), parts[1])
        if not result:
            send(token, chat, "Эта награда уже выбрана.", MENU)
        elif result["choice"] == "cash":
            send(token, chat,
                 f"✅ <b>{result['amount']} ₽ добавлены на баланс.</b>\n"
                 "Открой «Пригласить друга 💌», чтобы запросить выплату.", MENU)
        else:
            send(token, chat,
                 f"✅ <b>+{REF_BONUS} дней Premium</b>\n"
                 f"Доступ активен до <b>{result['until']}</b>.", MENU)
        return
    if (len(parts) == 3 and parts[0] == "ref_reward" and
            parts[1] in ("cash", "premium") and parts[2] == "start"):
        stats = ref_stats(uid)
        if not stats["choosing"]:
            send(token, chat, "Нет наград, ожидающих выбора.", MENU)
            return
        marker = ("КОЛИЧЕСТВО ДЛЯ ДЕНЕГ" if parts[1] == "cash" else
                  "КОЛИЧЕСТВО ДЛЯ PREMIUM")
        value = "100 ₽" if parts[1] == "cash" else f"+{REF_BONUS} дней"
        _PENDING_INPUT[chat] = f"reward:{parts[1]}"
        api(token, "sendMessage", {
            "chat_id": chat,
            "text": (f"🔢 <b>{marker}</b>\n\n"
                     f"Доступно рефералов: <b>{stats['choosing']}</b>.\n"
                     f"Каждый даст {value}. Следующим сообщением отправь число."),
            "parse_mode": "HTML",
        })
        return
    if data == "ref_payout:start":
        _PENDING_INPUT[chat] = "payout"
        api(token, "sendMessage", {
            "chat_id": chat,
            "text": ("💳 <b>РЕКВИЗИТЫ ВЫПЛАТЫ</b>\n\n"
                     "Следующим сообщением отправь номер телефона и название банка.\n"
                     "Пример: <code>+79991234567 · Сбербанк</code>"),
            "parse_mode": "HTML",
        })


def run_bot(token):
    _STATUS["running"] = True
    try:
        # Long polling cannot run while a webhook is configured for the bot.
        api(token, "deleteWebhook", {"drop_pending_updates": False}, timeout=20)
    except Exception as exc:
        _record_error(exc)
    offset = 0
    while True:
        try:
            upd = api(token, "getUpdates",
                       {"offset": offset, "timeout": 50, "allowed_updates":
                        ["message", "callback_query", "pre_checkout_query"]}, timeout=70)
            _STATUS["healthy"] = True
            _STATUS["last_poll"] = utc_iso()
            _STATUS["last_error"] = None
        except Exception as exc:
            _record_error(exc)
            time.sleep(5)
            continue
        for u in upd.get("result", []):
            offset = max(offset, u.get("update_id", 0) + 1)
            try:
                if "pre_checkout_query" in u:
                    q = u["pre_checkout_query"]
                    payment = {
                        "currency": q.get("currency"),
                        "total_amount": q.get("total_amount"),
                        "invoice_payload": q.get("invoice_payload"),
                    }
                    ok = validate_stars_payment(q["from"]["id"], payment) is not None
                    api(token, "answerPreCheckoutQuery",
                        {"pre_checkout_query_id": q["id"], "ok": ok,
                         **({} if ok else {"error_message":
                            "Не удалось проверить аккаунт или стоимость."})})
                elif "callback_query" in u:
                    handle_callback(token, u["callback_query"])
                elif "message" in u:
                    handle_message(token, u["message"])
            except Exception:
                continue
