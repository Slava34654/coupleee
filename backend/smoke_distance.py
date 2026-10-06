"""Дымовой тест расстояния: python backend/smoke_distance.py http://127.0.0.1:8000
Нужен запущенный сервер с обновлённым main.py. Использует только стандартную библиотеку."""
import json, sys, urllib.error, urllib.parse, urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

def call(method, path, body=None, **query):
    url = BASE + path + (("?" + urllib.parse.urlencode(query)) if query else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, None

def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)

s, a = call("POST", "/pair", {"name": "Тест-А"})
check(s == 200, "создана пара: пользователь A")
s, b = call("POST", "/pair/join", {"name": "Тест-Б", "code": a["pair_code"]})
check(s == 200, "пользователь B присоединился")
A, B = a["user_id"], b["user_id"]

s, d = call("GET", "/distance", user_id=A)
check(s == 200 and d["sharing"] is False and d["km"] is None, "до включения: sharing=false, km=null")

s, _ = call("POST", "/location", {"user_id": A, "lat": 52.2297, "lon": 21.0122})  # Варшава
check(s == 200, "A отправил точку (Варшава)")
s, d = call("GET", "/distance", user_id=A)
check(d["sharing"] and not d["partner_sharing"] and d["km"] is None,
      "делится только A: расстояния ещё нет")

s, _ = call("POST", "/location", {"user_id": B, "lat": 50.0647, "lon": 19.9450})  # Краков
check(s == 200, "B отправил точку (Краков)")
s, d = call("GET", "/distance", user_id=A)
check(d["km"] is not None and 245 <= d["km"] <= 260, f"расстояние Варшава–Краков ≈ 252 км, получено {d['km']}")
check(d["partner_name"] == "Тест-Б" and isinstance(d["partner_age_min"], int), "имя партнёра и возраст точки есть")
check("lat" not in json.dumps(d) and "lon" not in json.dumps(d), "координаты партнёра НЕ утекают в ответ")

s, _ = call("POST", "/location", {"user_id": A, "lat": 123, "lon": 0})
check(s == 400, "неверные координаты отклоняются (400)")
s, _ = call("POST", "/location", {"user_id": 999999, "lat": 1, "lon": 1})
check(s == 404, "неизвестный пользователь → 404")

s, _ = call("DELETE", "/location", user_id=A)
check(s == 200, "A выключил передачу")
s, d = call("GET", "/distance", user_id=B)
check(d["km"] is None and d["partner_sharing"] is False and d["sharing"] is True,
      "после выключения A у B расстояния нет")
s, _ = call("DELETE", "/location", user_id=B)
print("\nВсе проверки пройдены.")
