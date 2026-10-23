"""Focused checks for image uploads with unreliable Android MIME metadata."""
import os
import sys
import tempfile

os.environ["COUPLE_DB"] = os.path.join(tempfile.gettempdir(), "couple_photo_test.db")
os.environ["PHOTO_DIR"] = os.path.join(tempfile.gettempdir(), "couple_photo_test")
if os.path.exists(os.environ["COUPLE_DB"]):
    os.remove(os.environ["COUPLE_DB"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app, init_db


init_db()
client = TestClient(app)
registered = client.post(
    "/auth/register",
    json={"email": "photo-upload@example.com", "password": "secret123"},
).json()
headers = {"X-Auth-Token": registered["token"]}
png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

uploaded = client.post(
    "/photos",
    headers=headers,
    files={"file": ("image_picker_cache", png, "application/octet-stream")},
)
assert uploaded.status_code == 200, uploaded.text
assert uploaded.json()["url"].endswith(".png"), uploaded.text

rejected = client.post(
    "/photos",
    headers=headers,
    files={"file": ("fake.png", b"not an image", "image/png")},
)
assert rejected.status_code == 400, rejected.text

print("photo MIME fallback OK")
