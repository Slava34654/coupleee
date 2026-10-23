"""Auth security tests: login throttling and token expiration."""
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "auth.db"))
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def register_user(client, email="test@example.com", password="secret123"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response


def test_login_locks_email_after_five_failed_attempts(client):
    register_user(client)
    for _ in range(4):
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrong123"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrong123"},
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "900"


def test_unknown_email_attempts_are_limited(client):
    for _ in range(4):
        response = client.post(
            "/auth/login",
            json={"email": "missing@example.com", "password": "wrong123"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong123"},
    )
    assert response.status_code == 429


def test_successful_login_clears_failed_attempts(client):
    register_user(client, "reset@example.com")
    for _ in range(3):
        response = client.post(
            "/auth/login",
            json={"email": "reset@example.com", "password": "wrong123"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    for _ in range(4):
        response = client.post(
            "/auth/login",
            json={"email": "reset@example.com", "password": "wrong123"},
        )
        assert response.status_code == 401


def test_registered_token_expires_after_thirty_days(client):
    response = register_user(client, "expire@example.com")
    auth = response.json()
    now_ms = int(time.time() * 1000)

    con = sqlite3.connect(main.DB)
    expires_at = con.execute(
        "SELECT token_expires_at FROM users WHERE id=?",
        (auth["user_id"],),
    ).fetchone()[0]
    assert now_ms + main.TOKEN_TTL_MS - 5000 <= expires_at
    assert expires_at <= now_ms + main.TOKEN_TTL_MS + 5000
    con.execute("UPDATE users SET token_expires_at=1 WHERE id=?", (auth["user_id"],))
    con.commit()
    con.close()

    response = client.get(
        "/me",
        params={"user_id": auth["user_id"]},
        headers={"X-Auth-Token": auth["token"]},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "token expired"
