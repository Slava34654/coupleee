"""Isolated API test for the shared companion workflow."""
import os
import sys
import tempfile

os.environ["COUPLE_DB"] = os.path.join(tempfile.gettempdir(), "couple_companion_test.db")
if os.path.exists(os.environ["COUPLE_DB"]):
    os.remove(os.environ["COUPLE_DB"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app, init_db


init_db()
client = TestClient(app)

first = client.post("/pair", json={"name": "Алекс"}).json()
second = client.post(
    "/pair/join", json={"name": "Сэм", "code": first["pair_code"]}
).json()
a, b = first["user_id"], second["user_id"]
headers = {a: {"X-Auth-Token": first["token"]},
           b: {"X-Auth-Token": second["token"]}}


def get(uid):
    return client.get("/companion", params={"user_id": uid}, headers=headers[uid])


def post(path, uid, **values):
    return client.post(path, json={"user_id": uid, **values}, headers=headers[uid])


initial = get(a)
assert initial.status_code == 200, initial.text
assert not initial.json()["state"]["adopted"]
assert initial.json()["proposal"] is None

proposal = post("/companion/propose", a, type="PET", name="Плюша")
assert proposal.status_code == 200, proposal.text
assert proposal.json()["proposal"]["is_mine"]
assert not get(b).json()["proposal"]["is_mine"]
assert post("/companion/confirm", a).status_code == 409

# A partner can reject implicitly by replacing the proposal with their option.
counter = post("/companion/propose", b, type="BABY", name="Луна")
assert counter.status_code == 200, counter.text
adopted = post("/companion/confirm", a)
assert adopted.status_code == 200, adopted.text
assert adopted.json()["state"]["adopted"]
assert adopted.json()["state"]["type"] == "BABY"
assert adopted.json()["state"]["name"] == "Луна"

fed = post("/companion/action", b, action="feed")
assert fed.status_code == 200, fed.text
shared = get(a).json()["state"]
assert shared["hunger"] > .9
assert shared["coins"] == 22

renamed = post("/companion/action", a, action="rename", value="Солнышко")
assert renamed.status_code == 200, renamed.text
assert get(b).json()["state"]["name"] == "Солнышко"

reset = post("/companion/action", b, action="reset")
assert reset.status_code == 200, reset.text
assert not get(a).json()["state"]["adopted"]
assert get(a).json()["proposal"] is None

print("shared companion OK")
