import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "routes.db"))
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def register(client, email):
    response = client.post(
        "/auth/register", json={"email": email, "password": "secret123"}
    )
    assert response.status_code == 200
    return response.json()


def test_every_http_route_is_protected_or_explicitly_public():
    assert main.audit_http_routes() == main.PUBLIC_HTTP_ROUTES


def test_claimed_user_id_must_match_authenticated_user(client):
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")

    response = client.get(
        "/me",
        params={"user_id": second["user_id"]},
        headers={"X-Auth-Token": first["token"]},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "token does not belong to user_id"


def test_invalid_token_is_rejected_before_user_lookup(client):
    response = client.get(
        "/me",
        params={"user_id": 999999},
        headers={"X-Auth-Token": "invalid"},
    )
    assert response.status_code == 401
