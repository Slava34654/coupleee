"""Security regression test for explicit exact-location widget consent."""
import os
import sys
import tempfile

db_path = os.path.join(tempfile.gettempdir(), "couple_exact_location_test.db")
os.environ["COUPLE_DB"] = db_path
os.environ["ALLOW_INSECURE_EXACT_LOCATION"] = "1"
if os.path.exists(db_path):
    os.remove(db_path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app, db, init_db


init_db()
client = TestClient(app)


def auth(token):
    return {"X-Auth-Token": token}


a = client.post("/pair", json={"name": "A"}).json()
b = client.post("/pair/join", json={"name": "B", "code": a["pair_code"]}).json()
a_id, b_id = a["user_id"], b["user_id"]
a_headers, b_headers = auth(a["token"]), auth(b["token"])

# Exact disclosure is unavailable over plain HTTP in production.
os.environ.pop("ALLOW_INSECURE_EXACT_LOCATION")
r = client.post("/widget/location/consent", headers=a_headers, json={"user_id": a_id})
assert r.status_code == 426, r.text
os.environ["ALLOW_INSECURE_EXACT_LOCATION"] = "1"

# Ordinary distance sharing never creates exact-location consent.
r = client.post("/location", headers=a_headers,
                json={"user_id": a_id, "lat": 55.7558642, "lon": 37.6176981})
assert r.status_code == 200, r.text
r = client.get("/widget/location", headers=b_headers, params={"user_id": b_id})
assert r.status_code == 200 and not r.json()["partner_sharing"], r.text
con = db()
rounded = con.execute("SELECT lat,lon FROM locations WHERE user_id=?", (a_id,)).fetchone()
assert tuple(rounded) == (55.756, 37.618)
assert con.execute("SELECT 1 FROM exact_widget_shares").fetchone() is None
con.close()

# Consent is directional, bound to the current partner, and initially has no point.
r = client.post("/widget/location/consent", headers=a_headers, json={"user_id": a_id})
assert r.status_code == 200, r.text
r = client.get("/widget/location", headers=b_headers, params={"user_id": b_id})
assert r.json()["partner_sharing"] and r.json()["lat"] is None, r.text
r = client.get("/widget/location", headers=a_headers, params={"user_id": a_id})
assert not r.json()["partner_sharing"], r.text

client.post("/location", headers=a_headers,
            json={"user_id": a_id, "lat": 55.7558642, "lon": 37.6176981})
point = client.get("/widget/location", headers=b_headers,
                   params={"user_id": b_id}).json()
assert point["lat"] == 55.7558642 and point["lon"] == 37.6176981, point
assert point["updated_at"] and point["age_min"] == 0, point
assert point["my_lat"] is None and point["km"] is None, point

# With reciprocal consent, the widget receives both points and their distance.
client.post("/widget/location/consent", headers=b_headers, json={"user_id": b_id})
client.post("/location", headers=b_headers,
            json={"user_id": b_id, "lat": 55.7658642, "lon": 37.6276981})
point = client.get("/widget/location", headers=b_headers,
                   params={"user_id": b_id}).json()
assert point["my_lat"] == 55.7658642 and point["my_lon"] == 37.6276981, point
assert point["my_name"] == "B" and point["partner_name"] == "A", point
assert point["km"] is not None and point["km"] > 0, point

# A token can only read its own current partner relation.
r = client.get("/widget/location", headers=a_headers, params={"user_id": b_id})
assert r.status_code == 403, r.text

# Revocation immediately erases both consent and the exact point.
r = client.delete("/widget/location/consent", headers=a_headers,
                  params={"user_id": a_id})
assert r.status_code == 200, r.text
point = client.get("/widget/location", headers=b_headers,
                   params={"user_id": b_id}).json()
assert not point["partner_sharing"] and point["lat"] is None, point

# Stopping ordinary sharing also revokes exact sharing.
client.post("/widget/location/consent", headers=a_headers, json={"user_id": a_id})
client.post("/location", headers=a_headers,
            json={"user_id": a_id, "lat": 1.234567, "lon": 2.345678})
client.delete("/location", headers=a_headers, params={"user_id": a_id})
point = client.get("/widget/location", headers=b_headers,
                   params={"user_id": b_id}).json()
assert not point["partner_sharing"] and point["lat"] is None, point

# Pair removal deletes grants in both directions.
client.post("/widget/location/consent", headers=a_headers, json={"user_id": a_id})
client.post("/widget/location/consent", headers=b_headers, json={"user_id": b_id})
r = client.delete("/pair", headers=a_headers, params={"user_id": a_id})
assert r.status_code == 200, r.text
con = db()
assert con.execute("SELECT 1 FROM exact_widget_shares").fetchone() is None
con.close()

print("exact widget location OK")
