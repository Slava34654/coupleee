import datetime

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.time_utils import parse_utc, utc_iso


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "runtime-security.db"))
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def assert_security_headers(response):
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"]
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_json_responses_have_security_and_no_store_headers(client):
    public = client.get("/quiz-categories")
    assert public.status_code == 200
    assert_security_headers(public)
    assert public.headers["Cache-Control"] == "no-store"
    assert public.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )

    unauthorized = client.get("/me", params={"user_id": 1})
    assert unauthorized.status_code == 401
    assert_security_headers(unauthorized)


def test_hsts_is_only_sent_for_https(client):
    plain = client.get("/quiz-categories")
    assert "Strict-Transport-Security" not in plain.headers

    secure = client.get(
        "/quiz-categories", headers={"X-Forwarded-Proto": "https"}
    )
    assert secure.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_utc_helpers_emit_and_normalize_rfc3339():
    value = utc_iso()
    assert value.endswith("Z")
    assert parse_utc("2026-10-24T12:30:00").tzinfo == datetime.timezone.utc
    assert parse_utc("2026-10-24T15:30:00+03:00").isoformat() == (
        "2026-10-24T12:30:00+00:00"
    )


def test_new_activity_timestamps_are_utc(client):
    user = client.post("/pair", json={"name": "UTC user"}).json()
    response = client.post(
        "/mood",
        headers={"X-Auth-Token": user["token"]},
        json={"user_id": user["user_id"], "mood": "good"},
    )
    assert response.status_code == 200
    feed = client.get(
        "/moods",
        headers={"X-Auth-Token": user["token"]},
        params={"user_id": user["user_id"]},
    ).json()
    assert feed[0]["ts"].endswith("Z")
