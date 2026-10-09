"""Isolated API test for registering push notification tokens."""
import os
import sys
import tempfile

os.environ["COUPLE_DB"] = os.path.join(tempfile.gettempdir(), "couple_push_test.db")
if os.path.exists(os.environ["COUPLE_DB"]):
    os.remove(os.environ["COUPLE_DB"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app, db, init_db


init_db()
client = TestClient(app)
account = client.post("/pair", json={"name": "Алекс"}).json()
uid, token = account["user_id"], account["token"]
headers = {"X-Auth-Token": token}
device_token = "test-fcm-token-" + "x" * 40

registered = client.post(
    "/push/register",
    json={"user_id": uid, "token": device_token, "platform": "android"},
    headers=headers,
)
assert registered.status_code == 200, registered.text
con = db()
row = con.execute("SELECT * FROM push_tokens WHERE token=?", (device_token,)).fetchone()
con.close()
assert row and row["user_id"] == uid and row["platform"] == "android"

unregistered = client.post(
    "/push/unregister",
    json={"user_id": uid, "token": device_token, "platform": "android"},
    headers=headers,
)
assert unregistered.status_code == 200, unregistered.text
con = db()
row = con.execute("SELECT 1 FROM push_tokens WHERE token=?", (device_token,)).fetchone()
con.close()
assert row is None

print("push token API OK")
