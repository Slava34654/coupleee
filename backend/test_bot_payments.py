import datetime
import importlib
import os
import sqlite3
import sys
import tempfile
import types


DB = os.path.join(tempfile.gettempdir(), "enrwine_bot_payment_test.db")
os.environ["COUPLE_DB"] = DB
if os.path.exists(DB):
    os.remove(DB)

requests = types.ModuleType("requests")
requests.post = lambda *args, **kwargs: None
sys.modules.setdefault("requests", requests)

bot = importlib.import_module("bot")
from database import upgrade_database


def test_stars_payment_is_validated_and_idempotent():
    bot._record_error(Exception("https://api.telegram.org/botSECRET/getUpdates"))
    assert "SECRET" not in bot.bot_status()["last_error"]

    upgrade_database(DB)
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO users(id,name,pair_code,together_since,email) "
            "VALUES(1,'Алекс','BOT001','2026-01-01','a@example.com')"
        )
        con.execute("INSERT INTO tg(user_id,tg_id) VALUES(1,1001)")

    payment = {
        "currency": "XTR",
        "total_amount": 249,
        "invoice_payload": bot.stars_payload(1),
        "telegram_payment_charge_id": "charge-1",
        "provider_payment_charge_id": "",
    }
    calls = []
    original_api = bot.api
    bot.api = lambda token, method, payload=None, timeout=65: calls.append(
        (method, payload)
    )
    try:
        bot.send_stars_payment("token", 1001, 1)
    finally:
        bot.api = original_api
    assert calls[0][0] == "sendInvoice"
    assert calls[0][1]["currency"] == "XTR"
    assert calls[0][1]["prices"] == [
        {"label": "Premium на 1 мес.", "amount": 249}
    ]

    until, activated = bot.activate_stars_payment(1001, payment)
    assert activated is True
    assert until == (datetime.date.today() + datetime.timedelta(days=31)).isoformat()

    duplicate_until, activated = bot.activate_stars_payment(1001, payment)
    assert activated is False
    assert duplicate_until == until

    invalid = dict(payment, telegram_payment_charge_id="charge-2", total_amount=1)
    assert bot.activate_stars_payment(1001, invalid) == (None, False)

    six_months = {
        **payment,
        "total_amount": 1199,
        "invoice_payload": bot.stars_payload(1, "6"),
        "telegram_payment_charge_id": "charge-6",
    }
    six_until, activated = bot.activate_stars_payment(1001, six_months)
    assert activated is True
    assert six_until == (
        datetime.date.today() + datetime.timedelta(days=31 + 186)
    ).isoformat()

    with sqlite3.connect(DB) as con:
        assert con.execute("SELECT COUNT(*) FROM tg_payments").fetchone()[0] == 2
        assert con.execute(
            "SELECT premium_until FROM users WHERE id=1"
        ).fetchone()[0] == six_until

    assert "1448 ⭐" in bot.admin_stats()
    assert "Алекс" in bot.admin_payments()
    assert "a@example.com" in bot.admin_user("1")
    assert "Активные подписки" in bot.admin_subscribers()

    linked, message, linked_uid = bot.link_email(
        2002, "@telegram_nick", "a@example.com"
    )
    assert linked is True
    assert linked_uid == 1
    assert "@telegram_nick" in message
    assert "Алекс" not in message

    # A referrer without Premium can choose cash or bonus days after first sales.
    with sqlite3.connect(DB) as con:
        con.executemany(
            "INSERT INTO users(id,name,pair_code,together_since,email) VALUES(?,?,?,?,?)",
            [
                (2, "Реферер", "BOT002", "2026-01-01", "ref@example.com"),
                (3, "Друг 1", "BOT003", "2026-01-01", "friend1@example.com"),
                (4, "Друг 2", "BOT004", "2026-01-01", "friend2@example.com"),
                (5, "Друг 3", "BOT005", "2026-01-01", "friend3@example.com"),
            ],
        )
        con.executemany(
            "INSERT INTO tg(user_id,tg_id) VALUES(?,?)",
            [(2, 3002), (3, 3003), (4, 3004), (5, 3005)],
        )
        con.executemany(
            "INSERT INTO refs(tg_id,referrer) VALUES(?,?)",
            [(3003, 2), (3004, 2), (3005, 2)],
        )
    cash_reward = bot.create_referral_reward(3003, 3)
    assert cash_reward and bot.create_referral_reward(3003, 3) is None
    assert bot.choose_referral_reward(2, cash_reward["id"], "cash") == {
        "choice": "cash", "amount": 100,
    }
    assert bot.ref_stats(2)["available"] == 100
    payout, error = bot.create_referral_payout(2, "+79991234567 · Сбербанк")
    assert error is None and payout["amount"] == 100
    assert bot.ref_stats(2)["requested"] == 100
    paid = bot.admin_finish_payout(payout["id"])
    assert paid["status"] == "paid" and paid["tg_id"] == 3002
    assert bot.ref_stats(2)["paid"] == 100

    premium_reward = bot.create_referral_reward(3004, 4)
    premium_choice = bot.choose_referral_reward(2, premium_reward["id"], "premium")
    assert premium_choice["until"] == (
        datetime.date.today() + datetime.timedelta(days=7)
    ).isoformat()

    rejected_reward = bot.create_referral_reward(3005, 5)
    bot.choose_referral_reward(2, rejected_reward["id"], "cash")
    rejected_payout, error = bot.create_referral_payout(2, "+79991234567 · Сбербанк")
    assert error is None
    rejected = bot.admin_finish_payout(rejected_payout["id"], paid=False, note="Ошибка")
    assert rejected["status"] == "rejected"
    assert bot.ref_stats(2)["available"] == 100

    with sqlite3.connect(DB) as con:
        con.executemany(
            "INSERT INTO referral_rewards("
            "referred_tg_id,referrer_user_id,referred_user_id,created_at) "
            "VALUES(?,2,0,'2026-01-01')",
            [(-10,), (-11,), (-12,), (-13,)],
        )
    aggregate_cash, error = bot.choose_referral_rewards(2, "cash", 2)
    assert error is None
    assert aggregate_cash == {"choice": "cash", "count": 2, "amount": 200}
    aggregate_days, error = bot.choose_referral_rewards(2, "premium", 1)
    assert error is None and aggregate_days["days"] == 7
    assert bot.ref_stats(2)["choosing"] == 1

    dashboard_calls = []
    original_api = bot.api
    bot.api = lambda token, method, payload=None, timeout=20: dashboard_calls.append(
        (method, payload)
    )
    try:
        bot.send_referral_dashboard("token", 3002, 2)
    finally:
        bot.api = original_api
    reward_buttons = dashboard_calls[0][1]["reply_markup"]["inline_keyboard"][0]
    assert [button["callback_data"] for button in reward_buttons] == [
        "ref_reward:cash:start", "ref_reward:premium:start",
    ]

    bot._PENDING_INPUT.clear()
    dialog_calls = []
    original_api = bot.api
    bot.api = lambda token, method, payload=None, timeout=20: dialog_calls.append(
        (method, payload)
    )
    try:
        bot.handle_callback("token", {
            "id": "reward-choice",
            "from": {"id": 3002},
            "message": {"chat": {"id": 3002}},
            "data": "ref_reward:cash:start",
        })
        assert bot._PENDING_INPUT[3002] == "reward:cash"
        assert "force_reply" not in dialog_calls[1][1].get("reply_markup", {})
        bot.handle_message("token", {
            "chat": {"id": 3002, "first_name": "Referrer"},
            "text": "1",
        })
    finally:
        bot.api = original_api
    assert 3002 not in bot._PENDING_INPUT
    assert bot.ref_stats(2)["choosing"] == 0

    calls = []
    original_api = bot.api
    bot.api = lambda token, method, payload=None, timeout=65: calls.append(
        (method, payload)
    )
    try:
        bot.send_plan_picker("token", 2002)
        bot.handle_callback("token", {
            "id": "callback-1",
            "from": {"id": 2002},
            "message": {"chat": {"id": 2002}},
            "data": "premium:stars:3",
        })
    finally:
        bot.api = original_api
    assert len(calls[0][1]["reply_markup"]["inline_keyboard"]) == 3
    assert calls[0][1]["reply_markup"]["inline_keyboard"][2][1]["text"] == "1799 ₽"
    assert calls[1][0] == "answerCallbackQuery"
    assert calls[2][0] == "sendInvoice"
    assert calls[2][1]["prices"] == [{"label": "Premium на 3 мес.", "amount": 699}]

    sent = []
    original_send = bot.send
    bot.ADMIN_IDS = {1754701307}
    bot.send = lambda token, chat, text, buttons=None: sent.append((chat, text))
    try:
        bot.notify_admins("token", "new payment")
        bot.handle_message("token", {
            "chat": {"id": 1754701307, "first_name": "Admin"},
            "text": "/stats",
        })
    finally:
        bot.send = original_send
    assert sent[0] == (1754701307, "new payment")
    assert "Статистика Enrwine" in sent[1][1]

    calls = []
    original_api = bot.api
    bot.api = lambda token, method, payload=None, timeout=20: calls.append(
        (method, payload)
    )
    try:
        bot.send("token", 1754701307, "admin", bot.MENU)
    finally:
        bot.api = original_api
    admin_buttons = calls[0][1]["reply_markup"]["keyboard"][-1]
    assert [button["text"] for button in admin_buttons] == [
        "Ожидают выплаты 💳", "Выплаченные заявки ✅",
    ]

    sent = []
    original_send = bot.send
    bot.send = lambda token, chat, text, buttons=None: sent.append((chat, text))
    try:
        bot.handle_message("token", {
            "chat": {"id": 1754701307, "first_name": "Admin"},
            "text": "Ожидают выплаты 💳",
        })
        bot.handle_message("token", {
            "chat": {"id": 1001, "first_name": "User"},
            "text": "Выплаченные заявки ✅",
        })
    finally:
        bot.send = original_send
    assert "Реферальные выплаты" in sent[0][1]
    assert sent[1][1] == "Нет доступа 🔒"


def test_welcome_and_download_offer_the_application():
    calls = []
    original_api = bot.api
    bot.api = lambda token, method, payload=None, timeout=65: calls.append(
        (method, payload)
    )
    try:
        bot.send_welcome("token", 1001)
        bot.handle_message("token", {
            "chat": {"id": 1001, "first_name": "User"},
            "text": "/download",
        })
    finally:
        bot.api = original_api

    assert calls[0][0] == "sendPhoto"
    assert "Добро пожаловать" in calls[0][1]["caption"]
    assert calls[0][1]["reply_markup"]["inline_keyboard"][0][0]["url"].endswith(
        "/Enrwine.apk"
    )
    assert len(calls[0][1]["reply_markup"]["inline_keyboard"]) == 1
    assert "веб-верси" not in calls[0][1]["caption"].lower()
    assert calls[1][0] == "sendMessage"
    assert "Скачать Enrwine" in calls[1][1]["text"]
    assert len(calls[1][1]["reply_markup"]["inline_keyboard"]) == 1
