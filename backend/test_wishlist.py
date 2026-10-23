import os
import datetime
import sqlite3
import sys
import tempfile

os.environ["COUPLE_DB"] = os.path.join(tempfile.gettempdir(), "couple_wishlist_test.db")
if os.path.exists(os.environ["COUPLE_DB"]):
    os.remove(os.environ["COUPLE_DB"])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

from main import app, init_db


def test_wishlist_is_shared_and_isolated_by_couple():
    init_db()
    client = TestClient(app)

    first = client.post("/pair", json={"name": "Алекс"}).json()
    second = client.post(
        "/pair/join", json={"name": "Сэм", "code": first["pair_code"]}
    ).json()
    outsider = client.post("/pair", json={"name": "Другой"}).json()
    client.post(
        "/pair/join", json={"name": "Его пара", "code": outsider["pair_code"]}
    )

    def headers(user):
        return {"X-Auth-Token": user["token"]}

    premium_until = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    with sqlite3.connect(os.environ["COUPLE_DB"]) as con:
        con.execute(
            "UPDATE users SET premium_until=? WHERE id=?",
            (premium_until, first["user_id"]),
        )
    partner_premium = client.get(
        "/premium",
        params={"user_id": second["user_id"]},
        headers=headers(second),
    ).json()
    assert partner_premium["premium"] is True
    assert partner_premium["until"] == premium_until
    outsider_premium = client.get(
        "/premium",
        params={"user_id": outsider["user_id"]},
        headers=headers(outsider),
    ).json()
    assert outsider_premium["premium"] is False

    response = client.post(
        "/mood",
        json={"user_id": first["user_id"], "mood": "😊"},
        headers=headers(first),
    )
    assert response.status_code == 200, response.text
    only_one_active = client.get(
        "/me",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()
    assert only_one_active["streak"] == 0

    response = client.post(
        "/mood",
        json={"user_id": second["user_id"], "mood": "🥰"},
        headers=headers(second),
    )
    assert response.status_code == 200, response.text
    both_active = client.get(
        "/me",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()
    assert both_active["streak"] == 1

    response = client.post(
        "/profile/avatar",
        json={"user_id": first["user_id"], "avatar": "/photos/avatar.jpg"},
        headers=headers(first),
    )
    assert response.status_code == 200, response.text
    partner_view = client.get(
        "/me",
        params={"user_id": second["user_id"]},
        headers=headers(second),
    ).json()
    assert partner_view["partner"]["avatar"] == "/photos/avatar.jpg"

    response = client.post(
        "/wishlist",
        json={
            "user_id": first["user_id"],
            "title": "  Поездка к морю  ",
            "photo": "/photos/wish.jpg",
        },
        headers=headers(first),
    )
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]

    response = client.get(
        "/wishlist",
        params={"user_id": second["user_id"]},
        headers=headers(second),
    )
    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": item_id,
            "title": "Поездка к морю",
            "author_id": first["user_id"],
            "author": "Алекс",
            "photo": "/photos/wish.jpg",
            "done": False,
            "created_at": response.json()[0]["created_at"],
            "completed_at": "",
        }
    ]

    response = client.post(
        f"/wishlist/{item_id}/done",
        json={"user_id": second["user_id"], "done": True},
        headers=headers(second),
    )
    assert response.status_code == 200, response.text
    items = client.get(
        "/wishlist",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()
    assert items[0]["done"] is True
    assert items[0]["completed_at"]

    response = client.post(
        f"/wishlist/{item_id}/done",
        json={"user_id": outsider["user_id"], "done": False},
        headers=headers(outsider),
    )
    assert response.status_code == 404

    response = client.post(
        "/wishlist",
        json={"user_id": first["user_id"], "title": "   "},
        headers=headers(first),
    )
    assert response.status_code == 400
    assert client.get(
        "/wishlist", params={"user_id": first["user_id"]}
    ).status_code == 401

    response = client.delete(
        f"/wishlist/{item_id}",
        params={"user_id": second["user_id"]},
        headers=headers(second),
    )
    assert response.status_code == 200, response.text
    assert client.get(
        "/wishlist",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json() == []
