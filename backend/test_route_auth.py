import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

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


def test_every_protected_http_route_returns_401_without_token(client):
    failures = []
    for route in main.app.routes:
        if not isinstance(route, APIRoute):
            continue
        protected = any(
            dependency.call is main.current_user
            for dependency in route.dependant.dependencies
        )
        if not protected:
            continue
        path = route.path
        for parameter in route.param_convertors:
            path = path.replace("{" + parameter + "}", "1")
        method = sorted(route.methods - {"HEAD", "OPTIONS"})[0]
        response = client.request(method, path, json={})
        if response.status_code != 401:
            failures.append((method, route.path, response.status_code))
    assert failures == []


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


def test_current_user_returns_user_and_partner(client):
    first = register(client, "tuple-first@example.com")
    second_response = client.post(
        "/pair/join",
        json={"name": "Partner", "code": first["pair_code"]},
    )
    assert second_response.status_code == 200
    token = main._request_token.set(first["token"])
    try:
        me, partner = main.current_user()
    finally:
        main._request_token.reset(token)
    assert me["id"] == first["user_id"]
    assert partner["id"] == second_response.json()["user_id"]


def test_invalid_token_is_rejected_before_user_lookup(client):
    response = client.get(
        "/me",
        params={"user_id": 999999},
        headers={"X-Auth-Token": "invalid"},
    )
    assert response.status_code == 401
