"""Сквозной тест API: пара, настроение, вопрос, викторина, идеи, журнал, события."""
import os, sys, tempfile
# изолированная БД, чтобы не тереть живую couple.db
os.environ["COUPLE_DB"] = os.path.join(tempfile.gettempdir(), "couple_test.db")
if os.path.exists(os.environ["COUPLE_DB"]):
    os.remove(os.environ["COUPLE_DB"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app, init_db

init_db()
c = TestClient(app)

# все запросы от имени пользователя несут его токен (как в приложении)
TOK = {}
_raw_get, _raw_post, _raw_delete = c.get, c.post, c.delete
def _tok_headers(kwargs):
    p = kwargs.get("params") or {}
    j = kwargs.get("json") or {}
    uid = j.get("user_id", p.get("user_id") if isinstance(p, dict) else None)
    if uid in TOK:
        h = dict(kwargs.get("headers") or {})
        h["X-Auth-Token"] = TOK[uid]
        kwargs["headers"] = h
    return kwargs
def _g(*a, **k): return _raw_get(*a, **_tok_headers(k))
def _p(*a, **k): return _raw_post(*a, **_tok_headers(k))
def _d(*a, **k): return _raw_delete(*a, **_tok_headers(k))
c.get, c.post, c.delete = _g, _p, _d

r = c.post("/pair", json={"name": "Алекс"})
assert r.status_code == 200 and r.json()["token"], r.text  # дата рождения необязательна
r = c.post("/pair", json={"name": "Алекс", "birth": "не дата"})
assert r.status_code == 400
r = c.post("/pair", json={"name": "Алекс", "birth": "2000-05-10",
                          "avatar": "/photos/x.png"})
a = r.json(); print("pair A:", a)
assert a["user_id"] > 0 and a["token"]
r = c.post("/pair/join", json={"name": "Сэм", "code": a["pair_code"],
                               "birth": "2001-08-20"})
b = r.json(); print("pair B:", b)
assert b["token"]
A, B = a["user_id"], b["user_id"]
TOK[A], TOK[B] = a["token"], b["token"]

me = c.get("/me", params={"user_id": A}).json()
assert me["partner"]["id"] == B and me["days_together"] == 0, me
print("me OK:", me["name"], me["streak"])

assert c.post("/mood", json={"user_id": A, "mood": "😍", "note": "скучаю"}).json() == {"ok": True}
assert c.post("/mood", json={"user_id": B, "mood": "🥰"}).json() == {"ok": True}
me = c.get("/me", params={"user_id": A}).json()
assert me["my_mood"]["mood"] == "😍" and me["partner_mood"]["mood"] == "🥰"
assert me["streak"] == 1, me
print("mood+streak OK")

d = c.get("/daily", params={"user_id": A}).json()
assert d["my_answer"] is None and d["partner_answer"] is None
assert c.post("/daily/answer", json={"user_id": A, "text": "Наше первое кино"}).json() == {"ok": True}
d = c.get("/daily", params={"user_id": A}).json()
assert d["my_answer"] == "Наше первое кино" and d["partner_answer"] is None  # партнёр ещё не ответил
assert c.post("/daily/answer", json={"user_id": B, "text": "Поездка на море"}).json() == {"ok": True}
d = c.get("/daily", params={"user_id": A}).json()
assert d["partner_answer"] == "Поездка на море", d
print("daily OK:", d["question"]["text"][:40])

qs = c.get("/quizzes").json()
assert len(qs) == 2, qs
quiz = c.get(f"/quiz/{qs[0]['id']}", params={"user_id": A}).json()
assert len(quiz["questions"]) == 5
for i, qq in enumerate(quiz["questions"]):
    c.post(f"/quiz/{qs[0]['id']}/answer", json={"user_id": A, "qid": qq["id"], "option": 0})
    c.post(f"/quiz/{qs[0]['id']}/answer", json={"user_id": B, "qid": qq["id"], "option": 0 if i < 3 else 1})
res = c.get(f"/quiz/{qs[0]['id']}/result", params={"user_id": A}).json()
assert res["compatibility"] == 60, res
print("quiz OK:", res)

ideas = c.get("/ideas").json()
assert len(ideas) == 12, len(ideas)
rnd = c.get("/idea/random").json()
assert "title" in rnd
nid = c.post("/ideas", json={"title": "Каток", "category": "Активный отдых"}).json()["id"]
assert c.post(f"/idea/{nid}/done", params={"done": True}).json() == {"ok": True}
print("ideas OK:", rnd["title"])

jid = c.post("/journal", json={"user_id": A, "title": "Первый пост", "text": "Было здорово!"}).json()["id"]
j = c.get("/journal", params={"user_id": B}).json()
assert any(x["id"] == jid and x["author"] == "Алекс" for x in j)
print("journal OK")

import datetime
d10 = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
eid = c.post("/events", json={"user_id": A, "title": "Годовщина", "date": d10}).json()["id"]
ev = c.get("/events", params={"user_id": B}).json()
assert any(x["id"] == eid and x["days_left"] == 10 for x in ev), ev
print("events OK")

packs = c.get("/packs", params={"user_id": A}).json()
assert len(packs) == 9, len(packs)
kinds = {}
for p in packs:
    kinds[p["kind"]] = kinds.get(p["kind"], 0) + p["total"]
assert kinds == {"short": 46, "long": 12, "photo": 14}, kinds
short = c.get("/packs", params={"user_id": A, "kind": "short"}).json()
assert len(short) == 5 and all(p["kind"] == "short" for p in short)
c.get("/packs", params={"user_id": A})  # повторный сид не должен дублировать
import main as _m
_m.init_db()
assert len(c.get("/packs", params={"user_id": A}).json()) == 9
# фото-ответ
ph = next(p for p in packs if p["kind"] == "photo")
pk = c.get(f"/pack/{ph['id']}", params={"user_id": A}).json()
assert pk["kind"] == "photo"
qid = pk["questions"][0]["id"]
assert c.post(f"/pack/{ph['id']}/answer",
              json={"user_id": A, "qid": qid, "text": "мой кадр",
                    "photo": "/photos/fake.png"}).json() == {"ok": True}
pk = c.get(f"/pack/{ph['id']}", params={"user_id": A}).json()
assert pk["questions"][0]["my_photo"] == "/photos/fake.png"
assert pk["questions"][0]["partner_photo"] is None
assert c.post(f"/pack/{ph['id']}/answer",
              json={"user_id": B, "qid": qid, "photo": "/photos/fake2.png"}).json() == {"ok": True}
pk = c.get(f"/pack/{ph['id']}", params={"user_id": A}).json()
assert pk["questions"][0]["partner_photo"] == "/photos/fake2.png", pk
r = c.post(f"/pack/{ph['id']}/answer",
           json={"user_id": A, "qid": qid, "text": "", "photo": ""})
assert r.status_code == 400
pid = packs[0]["id"]
pk = c.get(f"/pack/{pid}", params={"user_id": A}).json()
assert len(pk["questions"]) == packs[0]["total"]
qid = pk["questions"][0]["id"]
assert c.post(f"/pack/{pid}/answer",
              json={"user_id": A, "qid": qid, "text": "Мой ответ"}).json() == {"ok": True}
pk = c.get(f"/pack/{pid}", params={"user_id": A}).json()
assert pk["questions"][0]["my_answer"] == "Мой ответ"
assert pk["questions"][0]["partner_answer"] is None  # партнёр ещё не ответил
assert c.post(f"/pack/{pid}/answer",
              json={"user_id": B, "qid": qid, "text": "Ответ партнёра"}).json() == {"ok": True}
pk = c.get(f"/pack/{pid}", params={"user_id": A}).json()
assert pk["questions"][0]["partner_answer"] == "Ответ партнёра", pk
packs = c.get("/packs", params={"user_id": A}).json()
assert packs[0]["answered_by_me"] == 1 and packs[0]["answered_together"] == 1
print("packs OK:", [(p["id"], p["total"]) for p in packs])

t = c.get("/tap", params={"user_id": A}).json()
assert t["partner_last"] is None and t["total"] == 0
assert c.post("/tap", json={"user_id": B}).json()["ok"] is True
t = c.get("/tap", params={"user_id": A}).json()
assert t["partner_last"] is not None and t["total"] == 1, t
print("tap OK")

feed = c.get("/moods", params={"user_id": A}).json()
assert len(feed) == 2 and feed[0]["author"] == "Сэм", feed
print("moods feed OK")

me = c.get("/me", params={"user_id": A}).json()
assert "together_since" in me
assert me["partner"]["age"] is not None and me["avatar"] == "/photos/x.png", me
pf = c.get("/partner", params={"user_id": A}).json()
assert pf["name"] == "Сэм" and pf["age"] is not None, pf
assert pf["moods"] == 1 and pf["moments"] >= 0 and pf["taps"] == 1, pf
print("partner profile OK:", pf["name"], pf["age"])
st = c.get("/stats", params={"user_id": A}).json()
assert st["answers"] == 6 and st["moods"] == 2 and st["moments"] == 1, st
assert st["avg_compatibility"] == 60 and st["quizzes_together"] == 1, st
print("stats OK:", st)

import asyncio
from main import wsman

class FakeWS:
    def __init__(self):
        self.msgs = []
    async def accept(self):
        pass
    async def send_json(self, m):
        self.msgs.append(m)

async def ws_scenario():
    fa, fb = FakeWS(), FakeWS()
    await wsman.connect(fa, A)
    await wsman.connect(fb, B)
    await wsman.ping_couple(A, "mood")
    assert any(m.get("what") == "mood" for m in fa.msgs), fa.msgs
    assert any(m.get("what") == "mood" for m in fb.msgs), fb.msgs
    wsman.drop(fa, A)
    wsman.drop(fb, B)
    return True

assert asyncio.run(ws_scenario())
print("websocket fan-out OK")

# журнал: лайки, избранное, поиск, фильтры, удаление
jid2 = c.post("/journal", json={"user_id": B, "title": "Морской закат",
                                "text": "Лучший вечер"}).json()["id"]
r = c.post(f"/journal/{jid2}/like", json={"user_id": A}).json()
assert r == {"liked": True, "likes": 1}, r
r = c.post(f"/journal/{jid2}/like", json={"user_id": A}).json()
assert r == {"liked": False, "likes": 0}, r
c.post(f"/journal/{jid2}/like", json={"user_id": B})
assert c.post(f"/journal/{jid2}/fav", json={"user_id": A}).json() == {"ok": True}
lst = c.get("/journal", params={"user_id": A}).json()
e2 = next(x for x in lst if x["id"] == jid2)
assert e2["likes"] == 1 and e2["liked_by_me"] is False and e2["fav"] == 1, e2
lst = c.get("/journal", params={"user_id": A, "q": "закат"}).json()
assert all("закат" in (x["title"] + x["text"]).lower() for x in lst) and lst
lst = c.get("/journal", params={"user_id": A, "author": "me"}).json()
assert all(x["author"] == "Алекс" for x in lst) and lst
lst = c.get("/journal", params={"user_id": A, "fav": True}).json()
assert all(x["fav"] == 1 for x in lst) and lst
r = c.delete(f"/journal/{jid2}", params={"user_id": A})
assert r.status_code == 403, r.status_code  # чужое удалять нельзя
assert c.delete(f"/journal/{jid2}", params={"user_id": B}).json() == {"ok": True}
print("journal extras OK")

# события: иконки, повторы, удаление
import datetime as _dt
past_bday = _dt.date.today().replace(year=_dt.date.today().year - 1).isoformat()
eid2 = c.post("/events", json={"user_id": A, "title": "ДР Сэма",
                               "date": past_bday, "icon": "🎂",
                               "repeat": True}).json()["id"]
ev = c.get("/events", params={"user_id": A}).json()
bday = next(x for x in ev if x["id"] == eid2)
assert bday["icon"] == "🎂" and bday["repeat"] is True, bday
assert 0 <= bday["days_left"] <= 366, bday  # ближайший следующий ДР
assert ev[0]["days_left"] >= 0  # будущие сверху
eid3 = c.post("/events", json={"user_id": B, "title": "Временное",
                               "date": "2030-01-01"}).json()["id"]
assert c.delete(f"/events/{eid3}", params={"user_id": A}).json() == {"ok": True}
ev = c.get("/events", params={"user_id": A}).json()
assert all(x["id"] != eid3 for x in ev)
print("events extras OK:", bday["id"], bday["days_left"], bday["date"])

# фото: загрузка, привязка к записи, проверки
png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
r = c.post("/photos", params={"user_id": A}, files={"file": ("pic.png", png, "image/png")})
assert r.status_code == 200, r.text
url = r.json()["url"]
assert url.startswith("/photos/") and url.endswith(".png"), url
rj = c.get(url)
assert rj.status_code == 200 and rj.content[:8] == png[:8]
r = c.post("/photos", params={"user_id": A}, files={"file": ("x.txt", b"hi", "text/plain")})
assert r.status_code == 400
r = c.post("/photos", params={"user_id": A}, files={"file": ("big.png", b"\x00" * (6 * 1024 * 1024), "image/png")})
assert r.status_code == 400
r = c.post("/photos", files={"file": ("pic.png", png, "image/png")})
assert r.status_code in (401, 404), r.status_code  # загрузка без авторизации закрыта
jid3 = c.post("/journal", json={"user_id": A, "title": "С фото",
                                "text": "смотри", "photo": url}).json()["id"]
lst = c.get("/journal", params={"user_id": A}).json()
assert next(x for x in lst if x["id"] == jid3)["photo"] == url
print("photos OK:", url)

r = c.get("/manifest.webmanifest")
assert r.status_code == 200 and r.json()["short_name"] == "CoupleJoy", r.status_code
r = c.get("/sw.js")
assert r.status_code == 200 and "service worker" in r.text.lower()
r = c.get("/icons/icon-192.png")
assert r.status_code == 200 and r.headers["content-type"] == "image/png"
r = c.get("/icons/nope.png")
assert r.status_code == 404
print("pwa OK")

r = c.post("/widget", json={"user_id": A, "photo": "/photos/w1.png",
                            "caption": "смотри!"})
assert r.json()["ok"] is True
r = c.post("/widget", json={"user_id": A, "photo": ""})
assert r.status_code == 400
w = c.get("/widget", params={"user_id": B}).json()
assert w["partner"]["photo"] == "/photos/w1.png", w
assert w["partner"]["caption"] == "смотри!" and w["mine"] is None
w = c.get("/widget", params={"user_id": A}).json()
assert w["mine"]["photo"] == "/photos/w1.png" and w["partner"] is None
print("widget photos OK")

# авторизация: без токена и с чужим токеном — 401, перебор id закрыт
c0 = TestClient(app)
assert c0.get("/me", params={"user_id": A}).status_code == 401
assert c0.get("/me", params={"user_id": A},
              headers={"X-Auth-Token": "wrong"}).status_code == 401
assert c0.get("/me", params={"user_id": B},
              headers={"X-Auth-Token": TOK[A]}).status_code == 401  # чужой токен
assert c0.get("/me", params={"user_id": 999999},
              headers={"X-Auth-Token": "x"}).status_code == 404
assert c0.get("/journal", params={"user_id": A}).status_code == 401
print("auth OK: 401 without token, чужой токен отклонён")

r = c.delete("/pair", params={"user_id": A})
assert r.json() == {"ok": True}
assert r.json() == {"ok": True}
me = c.get("/me", params={"user_id": A}).json()
assert me["partner"] is None
me = c.get("/me", params={"user_id": B}).json()
assert me["partner"] is None
print("pair leave OK")
print("ALL BACKEND TESTS PASSED")
