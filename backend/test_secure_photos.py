import os
import time

import pytest
from fastapi.testclient import TestClient

from backend import main


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "secure-photos.db"))
    monkeypatch.setattr(main, "PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setattr(main, "PHOTO_UPLOAD_TOKEN_LEGACY", False)
    monkeypatch.setattr(main, "PHOTO_URL_HMAC_SECRET", b"test-photo-secret")
    monkeypatch.setattr(main, "_s3", None)
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def register(client):
    response = client.post(
        "/auth/register",
        json={"email": "photos@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    return response.json()


def auth(user):
    return {"X-Auth-Token": user["token"]}


def upload_token(client, user):
    response = client.post("/photos/upload-token", headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()["upload_token"]


def upload(client, token, content=PNG):
    return client.post(
        "/photos",
        headers={"X-Photo-Upload-Token": token},
        files={"file": ("photo.png", content, "image/png")},
    )


def test_upload_token_is_required_and_single_use(client):
    user = register(client)
    missing = client.post(
        "/photos",
        headers=auth(user),
        files={"file": ("photo.png", PNG, "image/png")},
    )
    assert missing.status_code == 401

    token = upload_token(client, user)
    uploaded = upload(client, token)
    assert uploaded.status_code == 200, uploaded.text
    assert upload(client, token).status_code == 401


def test_signed_url_allows_temporary_anonymous_read(client):
    user = register(client)
    uploaded = upload(client, upload_token(client, user)).json()

    response = client.get(uploaded["signed_url"])
    assert response.status_code == 200
    assert response.content == PNG

    name = uploaded["url"].rsplit("/", 1)[-1]
    expired = main.signed_photo_url(name, int(time.time()) - 1)
    assert client.get(expired).status_code == 401
    assert client.get(uploaded["signed_url"] + "&sig=duplicate").status_code == 401


def test_oversized_upload_is_removed_and_token_is_consumed(client, monkeypatch):
    monkeypatch.setattr(main, "PHOTO_MAX_BYTES", 64)
    user = register(client)
    token = upload_token(client, user)

    response = upload(client, token, PNG)
    assert response.status_code == 400
    assert not [name for name in os.listdir(main.PHOTO_DIR) if name.startswith(".upload-")]
    assert upload(client, token, b"\x89PNG\r\n\x1a\n").status_code == 401


def test_upload_token_rate_limit_returns_retry_after(client, monkeypatch):
    monkeypatch.setattr(main, "PHOTO_UPLOAD_USER_LIMIT", 1)
    user = register(client)
    assert client.post("/photos/upload-token", headers=auth(user)).status_code == 200

    response = client.post("/photos/upload-token", headers=auth(user))
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_storage_quota_is_checked_before_issuing_token(client, monkeypatch):
    monkeypatch.setattr(main, "PHOTO_USER_QUOTA_BYTES", main.PHOTO_MAX_BYTES - 1)
    user = register(client)

    response = client.post("/photos/upload-token", headers=auth(user))
    assert response.status_code == 413
