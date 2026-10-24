import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "websocket.db"))
    main.wsman.conns.clear()
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client
    main.wsman.conns.clear()


def register(client):
    response = client.post(
        "/auth/register",
        json={"email": "socket@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    return response.json()


def test_first_message_authenticates_and_derives_user_id(client):
    user = register(client)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"type": "auth", "token": user["token"], "user_id": 999})
        assert socket.receive_json() == {
            "type": "authenticated",
            "user_id": user["user_id"],
        }
        socket.send_json({"type": "ping"})


def test_invalid_token_is_closed_as_unauthorized(client):
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"type": "auth", "token": "invalid"})
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
    assert error.value.code == 4401


def test_query_credentials_are_not_accepted(client):
    user = register(client)
    with client.websocket_connect(
        f"/ws?user_id={user['user_id']}&token={user['token']}"
    ) as socket:
        socket.send_text("ping")
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
    assert error.value.code == 1008


def test_expired_session_cannot_authenticate(client):
    user = register(client)
    with sqlite3.connect(main.DB) as con:
        con.execute(
            "UPDATE users SET token_expires_at=1 WHERE id=?", (user["user_id"],)
        )

    with client.websocket_connect("/ws") as socket:
        socket.send_text(json.dumps({"type": "auth", "token": user["token"]}))
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
    assert error.value.code == 4401


def test_authentication_times_out(client, monkeypatch):
    monkeypatch.setattr(main, "WS_AUTH_TIMEOUT_SECONDS", 0.01)
    with client.websocket_connect("/ws") as socket:
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
    assert error.value.code == 4408


def test_authenticated_connection_has_idle_timeout(client, monkeypatch):
    monkeypatch.setattr(main, "WS_IDLE_TIMEOUT_SECONDS", 0.01)
    user = register(client)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"type": "auth", "token": user["token"]})
        assert socket.receive_json()["type"] == "authenticated"
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
    assert error.value.code == 4408
