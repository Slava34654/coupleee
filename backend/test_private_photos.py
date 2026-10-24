import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import main


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "photos.db"))
    monkeypatch.setattr(main, "PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setattr(main, "PHOTOS_PUBLIC_LEGACY", False)
    monkeypatch.setattr(main, "_s3", None)
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def register(client, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth(user):
    return {"X-Auth-Token": user["token"]}


def upload(client, user):
    issued = client.post("/photos/upload-token", headers=auth(user))
    assert issued.status_code == 200, issued.text
    response = client.post(
        "/photos",
        headers={"X-Photo-Upload-Token": issued.json()["upload_token"]},
        files={"file": ("photo.png", PNG, "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()["url"]


def set_pair(first, second):
    con = sqlite3.connect(main.DB)
    con.execute("UPDATE users SET partner_id=? WHERE id=?", (second, first))
    con.execute("UPDATE users SET partner_id=? WHERE id=?", (first, second))
    con.commit()
    con.close()


def test_photo_requires_authentication_and_hides_foreign_media(client):
    owner = register(client, "owner@example.com")
    stranger = register(client, "stranger@example.com")

    anonymous_upload = client.post(
        "/photos", files={"file": ("photo.png", PNG, "image/png")}
    )
    assert anonymous_upload.status_code == 401

    url = upload(client, owner)
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth(stranger)).status_code == 404
    response = client.get(url, headers=auth(owner))
    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["cache-control"] == "private, no-store"


def test_legacy_public_switch_allows_unsigned_links(client, monkeypatch):
    owner = register(client, "legacy-owner@example.com")
    url = upload(client, owner)
    monkeypatch.setattr(main, "PHOTOS_PUBLIC_LEGACY", True)
    assert client.get(url).status_code == 200


def test_only_current_mutual_partner_can_read_photo(client):
    owner = register(client, "owner@example.com")
    partner = register(client, "partner@example.com")
    url = upload(client, owner)

    set_pair(owner["user_id"], partner["user_id"])
    assert client.get(url, headers=auth(partner)).status_code == 200

    con = sqlite3.connect(main.DB)
    con.execute("UPDATE users SET partner_id=NULL WHERE id=?", (owner["user_id"],))
    con.commit()
    con.close()
    assert client.get(url, headers=auth(partner)).status_code == 404


def test_referencing_a_foreign_photo_does_not_grant_access(client):
    owner = register(client, "owner@example.com")
    stranger = register(client, "stranger@example.com")
    url = upload(client, owner)

    con = sqlite3.connect(main.DB)
    con.execute(
        "INSERT INTO journal(user_id,title,text,photo,ts) VALUES(?,?,?,?,?)",
        (stranger["user_id"], "stolen", "", url, "2026-10-24T12:00:00"),
    )
    con.commit()
    con.close()

    assert client.get(url, headers=auth(stranger)).status_code == 404
