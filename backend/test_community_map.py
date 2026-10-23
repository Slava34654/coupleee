import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture()
def map_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "community-map.db"))
    main.init_db()
    with TestClient(main.app) as client:
        yield client


def create_pair(client, first_name="Alex", second_name="Sam"):
    first = client.post("/pair", json={"name": first_name}).json()
    second = client.post(
        "/pair/join", json={"name": second_name, "code": first["pair_code"]}
    ).json()
    return first, second


def headers(user):
    return {"X-Auth-Token": user["token"]}


def photo():
    return f"/photos/{uuid.uuid4().hex}.jpg"


def create_post(client, user, lat=55.7558, lon=37.6173, **changes):
    body = {
        "user_id": user["user_id"],
        "lat": lat,
        "lon": lon,
        "photo": photo(),
        "comment": "Our favorite journey",
        "public_consent": True,
    }
    body.update(changes)
    return client.post("/community/map", headers=headers(user), json=body)


def approve(client, user, post_id):
    return client.post(
        f"/community/map/{post_id}/approve",
        headers=headers(user),
        json={"user_id": user["user_id"]},
    )


def listing(client, user):
    return client.get(
        "/community/map",
        headers=headers(user),
        params={"user_id": user["user_id"]},
    )


def test_auth_country_catalog_and_private_response(map_api):
    client = map_api
    first, second = create_pair(client, "A" * 60, "Private Partner")

    assert client.get(
        "/community/map/countries", params={"user_id": first["user_id"]}
    ).status_code == 401
    assert client.get(
        "/community/map",
        headers=headers(second),
        params={"user_id": first["user_id"]},
    ).status_code == 401

    countries = client.get(
        "/community/map/countries",
        headers=headers(first),
        params={"user_id": first["user_id"]},
    ).json()
    assert len(countries) >= 50
    assert {"RU", "BY", "UA", "KZ", "US", "ZA", "AU"} <= {
        country["code"] for country in countries
    }
    assert set(countries[0]) == {"code", "name_ru", "name_en", "lat", "lon"}

    post = create_post(client, first).json()
    assert set(post) == {
        "id",
        "country_code",
        "country_name_ru",
        "country_name_en",
        "lat",
        "lon",
        "photo",
        "comment",
        "couple_name",
        "updated_at",
        "mine",
        "published",
        "can_approve",
        "likes_count",
        "liked_by_me",
        "comments_count",
    }
    assert "pair_code" not in str(post)
    assert "email" not in str(post)
    assert len(post["couple_name"].split(" & ")[0]) == 40
    assert post["likes_count"] == 0
    assert post["liked_by_me"] is False
    assert post["comments_count"] == 0


def test_pending_is_private_until_second_approval(map_api):
    client = map_api
    first, second = create_pair(client)
    outsider, _ = create_pair(client, "Other", "Pair")

    response = create_post(client, first)
    assert response.status_code == 200, response.text
    post = response.json()
    assert post["mine"] is True
    assert post["published"] is False
    assert post["can_approve"] is False
    assert listing(client, second).json()[0]["can_approve"] is True
    assert listing(client, outsider).json() == []

    published = approve(client, second, post["id"])
    assert published.status_code == 200, published.text
    assert published.json()["published"] is True
    outsider_post = listing(client, outsider).json()[0]
    assert outsider_post["mine"] is False
    assert outsider_post["can_approve"] is False


def test_coordinates_keep_full_precision(map_api):
    client = map_api
    first, _ = create_pair(client)
    lat = 55.751244123456
    lon = 37.618423654321

    post = create_post(client, first, lat=lat, lon=lon).json()

    assert post["lat"] == lat
    assert post["lon"] == lon
    assert listing(client, first).json()[0]["lat"] == lat
    assert listing(client, first).json()[0]["lon"] == lon


@pytest.mark.parametrize(
    "changes",
    [
        {"lat": 200},
        {"lon": 200},
        {"lat": 91},
        {"photo": "https://example.com/photo.jpg"},
        {"photo": "/photos/not-a-uuid.jpg"},
        {"comment": "   "},
        {"comment": "x" * 501},
        {"comment": "hello\nworld"},
        {"public_consent": False},
    ],
)
def test_post_validation(map_api, changes):
    client = map_api
    first, _ = create_pair(client)
    assert create_post(client, first, **changes).status_code == 400


def test_upsert_resets_other_approval(map_api):
    client = map_api
    first, second = create_pair(client)
    original = create_post(client, first).json()
    assert approve(client, second, original["id"]).json()["published"] is True

    changed = create_post(
        client,
        second,
        photo=photo(),
        comment="  Updated by partner  ",
    )
    assert changed.status_code == 200, changed.text
    payload = changed.json()
    assert payload["id"] == original["id"]
    assert payload["comment"] == "Updated by partner"
    assert payload["published"] is False
    assert listing(client, first).json()[0]["can_approve"] is True
    with sqlite3.connect(main.DB) as con:
        assert con.execute("SELECT COUNT(*) FROM community_map_posts").fetchone()[0] == 1


def test_pair_cannot_add_more_than_thirty_points(map_api):
    client = map_api
    first, second = create_pair(client)
    low, high = sorted((first["user_id"], second["user_id"]))
    with sqlite3.connect(main.DB) as con:
        con.executemany(
            "INSERT INTO community_map_posts(pair_low_id,pair_high_id,"
            "created_by_user_id,country_code,lat,lon,photo,comment,low_approved,"
            "high_approved,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,1,1,?,?)",
            [
                (
                    low,
                    high,
                    first["user_id"],
                    "",
                    55.0 + i * 0.001,
                    37.0 + i * 0.001,
                    photo(),
                    "Trip",
                    "2026-01-01",
                    "2026-01-01",
                )
                for i in range(30)
            ],
        )

    response = create_post(client, first, lat=60.0, lon=30.0)
    assert response.status_code == 409


def test_public_select_requires_owners_to_still_be_mutual(map_api):
    client = map_api
    owner, partner = create_pair(client)
    outsider, _ = create_pair(client, "Other", "Pair")
    post_id = create_post(client, owner).json()["id"]
    approve(client, partner, post_id)
    assert listing(client, outsider).json()[0]["id"] == post_id

    with sqlite3.connect(main.DB) as con:
        con.execute(
            "UPDATE users SET partner_id=NULL WHERE id=?", (partner["user_id"],)
        )
    assert listing(client, outsider).json() == []


def test_only_owner_can_delete(map_api):
    client = map_api
    first, second = create_pair(client)
    outsider, _ = create_pair(client, "Other", "Pair")
    post_id = create_post(client, first).json()["id"]

    denied = client.delete(
        f"/community/map/{post_id}",
        headers=headers(outsider),
        params={"user_id": outsider["user_id"]},
    )
    assert denied.status_code == 404
    deleted = client.delete(
        f"/community/map/{post_id}",
        headers=headers(second),
        params={"user_id": second["user_id"]},
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}


def test_three_unique_reports_hide_published_post(map_api):
    client = map_api
    owner, partner = create_pair(client, "Owner", "Partner")
    reporters = [create_pair(client, f"Reporter {i}", f"R pair {i}")[0] for i in range(3)]
    post_id = create_post(client, owner).json()["id"]
    approve(client, partner, post_id)

    report_url = f"/community/map/{post_id}/report"
    for reporter in reporters[:2]:
        response = client.post(
            report_url,
            headers=headers(reporter),
            json={"user_id": reporter["user_id"], "reason": "privacy"},
        )
        assert response.status_code == 200, response.text
    duplicate = client.post(
        report_url,
        headers=headers(reporters[0]),
        json={"user_id": reporters[0]["user_id"], "reason": "spam"},
    )
    assert duplicate.status_code == 200
    assert len(listing(client, reporters[0]).json()) == 1

    third = client.post(
        report_url,
        headers=headers(reporters[2]),
        json={"user_id": reporters[2]["user_id"], "reason": "inappropriate"},
    )
    assert third.status_code == 200
    assert listing(client, reporters[0]).json() == []
    assert listing(client, owner).json() == []
    with sqlite3.connect(main.DB) as con:
        assert con.execute(
            "SELECT COUNT(*) FROM community_map_reports WHERE post_id=?", (post_id,)
        ).fetchone()[0] == 3
        assert con.execute(
            "SELECT hidden FROM community_map_posts WHERE id=?", (post_id,)
        ).fetchone()[0] == 1


def test_pair_leave_removes_posts_and_reports(map_api):
    client = map_api
    owner, partner = create_pair(client)
    reporter, _ = create_pair(client, "Reporter", "Reporter pair")
    post_id = create_post(client, owner).json()["id"]
    approve(client, partner, post_id)
    client.post(
        f"/community/map/{post_id}/report",
        headers=headers(reporter),
        json={"user_id": reporter["user_id"], "reason": "other"},
    )

    response = client.delete(
        "/pair", headers=headers(owner), params={"user_id": owner["user_id"]}
    )
    assert response.status_code == 200, response.text
    with sqlite3.connect(main.DB) as con:
        assert con.execute("SELECT 1 FROM community_map_posts").fetchone() is None
        assert con.execute("SELECT 1 FROM community_map_reports").fetchone() is None


def test_other_users_can_like_and_comment_on_published_posts(map_api):
    client = map_api
    owner, partner = create_pair(client, "Owner", "Partner")
    visitor, _ = create_pair(client, "Visitor", "Visitor pair")
    post_id = create_post(client, owner).json()["id"]
    approve(client, partner, post_id)

    like_url = f"/community/map/{post_id}/like"
    liked = client.post(
        like_url,
        headers=headers(visitor),
        json={"user_id": visitor["user_id"], "liked": True},
    )
    assert liked.status_code == 200, liked.text
    assert liked.json() == {
        "post_id": post_id,
        "liked_by_me": True,
        "likes_count": 1,
    }
    assert client.post(
        like_url,
        headers=headers(visitor),
        json={"user_id": visitor["user_id"], "liked": True},
    ).json()["likes_count"] == 1

    comments_url = f"/community/map/{post_id}/comments"
    added = client.post(
        comments_url,
        headers=headers(visitor),
        json={"user_id": visitor["user_id"], "text": "  Красивое место!  "},
    )
    assert added.status_code == 200, added.text
    comment = added.json()
    assert comment["text"] == "Красивое место!"
    assert comment["author_name"] == "Visitor"
    assert comment["mine"] and comment["can_delete"] and not comment["can_report"]
    assert "author_user_id" not in comment

    owner_comments = client.get(
        comments_url,
        headers=headers(owner),
        params={"user_id": owner["user_id"]},
    ).json()
    assert owner_comments[0]["can_delete"] is True
    assert owner_comments[0]["can_report"] is False
    post = listing(client, visitor).json()[0]
    assert post["likes_count"] == 1 and post["liked_by_me"] is True
    assert post["comments_count"] == 1

    assert client.post(
        like_url,
        headers=headers(owner),
        json={"user_id": owner["user_id"], "liked": True},
    ).status_code == 404
    assert client.post(
        comments_url,
        headers=headers(owner),
        json={"user_id": owner["user_id"], "text": "self"},
    ).status_code == 404

    deleted = client.delete(
        f"{comments_url}/{comment['id']}",
        headers=headers(owner),
        params={"user_id": owner["user_id"]},
    )
    assert deleted.status_code == 200
    assert listing(client, visitor).json()[0]["comments_count"] == 0

    unliked = client.post(
        like_url,
        headers=headers(visitor),
        json={"user_id": visitor["user_id"], "liked": False},
    ).json()
    assert unliked["likes_count"] == 0 and unliked["liked_by_me"] is False


def test_comments_are_validated_and_three_reports_hide_them(map_api):
    client = map_api
    owner, partner = create_pair(client, "Owner", "Partner")
    author, _ = create_pair(client, "Author", "Author pair")
    reporters = [create_pair(client, f"Reporter {i}", f"Pair {i}")[0] for i in range(3)]
    post_id = create_post(client, owner).json()["id"]
    approve(client, partner, post_id)
    comments_url = f"/community/map/{post_id}/comments"

    for text in ("   ", "x" * 301, "hello\nworld"):
        response = client.post(
            comments_url,
            headers=headers(author),
            json={"user_id": author["user_id"], "text": text},
        )
        assert response.status_code == 400

    comment_id = client.post(
        comments_url,
        headers=headers(author),
        json={"user_id": author["user_id"], "text": "Public comment"},
    ).json()["id"]
    report_url = f"{comments_url}/{comment_id}/report"
    for reporter in reporters:
        response = client.post(
            report_url,
            headers=headers(reporter),
            json={"user_id": reporter["user_id"], "reason": "spam"},
        )
        assert response.status_code == 200, response.text

    assert client.get(
        comments_url,
        headers=headers(reporters[0]),
        params={"user_id": reporters[0]["user_id"]},
    ).json() == []
    assert listing(client, reporters[0]).json()[0]["comments_count"] == 0
