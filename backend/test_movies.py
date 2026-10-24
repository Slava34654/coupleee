import sqlite3

import pytest
from fastapi.testclient import TestClient

import main


class FakeMovieProvider:
    def __init__(self):
        self.movies = [
            self.movie(101, "Космос", ["фантастика", "драма"]),
            self.movie(102, "Будущее", ["фантастика"]),
            self.movie(103, "Смех", ["комедия"]),
            self.movie(104, "История", ["драма"]),
            self.movie(105, "Погоня", ["боевик"]),
            self.movie(106, "Любовь", ["мелодрама"]),
            self.movie(107, "Кошмар", ["ужасы"]),
        ]

    @staticmethod
    def movie(movie_id, title, genres):
        return {
            "id": movie_id,
            "title": title,
            "title_en": title,
            "overview": "Описание",
            "overview_en": "Overview",
            "release_year": 2025,
            "poster_url": f"https://example.com/{movie_id}.jpg",
            "genres": genres,
            "runtime_min": None,
            "rating": 8.0,
            "rating_source": "TMDB",
        }

    def catalog(self, genre_key):
        genre = main.MOVIE_GENRES[genre_key][0].lower()
        if genre_key == "all":
            return self.movies
        return [movie for movie in self.movies if genre in movie["genres"]]

    def genre_options(self):
        result = []
        for key, (title, title_en, _) in main.MOVIE_GENRES.items():
            count = len(self.catalog(key))
            if count:
                result.append({
                    "key": key,
                    "title": title,
                    "title_en": title_en,
                    "movie_count": count,
                })
        return result


@pytest.fixture
def movie_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "movies.db"))
    monkeypatch.setattr(main, "movie_provider", FakeMovieProvider())
    main.init_db()
    topics = []

    async def record_ping(user_id, what="all"):
        topics.append((user_id, what))

    monkeypatch.setattr(main.wsman, "ping_couple", record_ping)
    return TestClient(main.app), topics


def create_pair(client, first_name="Alex", second_name="Sam"):
    first = client.post("/pair", json={"name": first_name}).json()
    second = client.post(
        "/pair/join", json={"name": second_name, "code": first["pair_code"]}
    ).json()
    return first, second


def headers(user):
    return {"X-Auth-Token": user["token"]}


def state(client, user):
    return client.get(
        "/movies/state", params={"user_id": user["user_id"]}, headers=headers(user)
    )


def swipe(client, user, movie_id, direction):
    return client.post(
        "/movies/swipe",
        json={
            "user_id": user["user_id"],
            "movie_id": movie_id,
            "direction": direction,
        },
        headers=headers(user),
    )


def select_genre(client, user, genre_key="drama"):
    return client.post(
        "/movies/genre",
        json={"user_id": user["user_id"], "genre_key": genre_key},
        headers=headers(user),
    )


def test_auth_and_reciprocal_pair_isolation(movie_api):
    client, _ = movie_api
    first, second = create_pair(client)
    outsider, outsider_partner = create_pair(client, "Other", "Other partner")

    assert client.get(
        "/movies/state", params={"user_id": first["user_id"]}
    ).status_code == 401
    assert client.get(
        "/movies/state",
        params={"user_id": first["user_id"]},
        headers=headers(outsider),
    ).status_code == 403

    first_state = state(client, first).json()
    second_state = state(client, second).json()
    outsider_state = state(client, outsider).json()
    assert first_state["round_id"] == second_state["round_id"]
    assert first_state["round_id"] != outsider_state["round_id"]
    assert first_state["partner_name"] == "Sam"
    assert state(client, outsider_partner).json()["round_id"] == outsider_state["round_id"]


def test_direction_semantics_and_independent_traversal(movie_api):
    client, topics = movie_api
    first, second = create_pair(client)
    initial = select_genre(client, first).json()
    first_movie = initial["movie"]["id"]

    heart = swipe(client, first, first_movie, "left")
    assert heart.status_code == 200, heart.text
    assert heart.json()["status"] == "active"
    assert heart.json()["match"] is None
    assert heart.json()["swiped_count"] == 1
    assert heart.json()["movie"]["id"] != first_movie

    partner_state = state(client, second).json()
    assert partner_state["swiped_count"] == 0
    assert partner_state["movie"]["id"] == first_movie
    skipped = swipe(client, second, first_movie, "right")
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["status"] == "active"
    assert skipped.json()["match"] is None

    with sqlite3.connect(main.DB) as con:
        decisions = con.execute(
            "SELECT user_id,decision FROM movie_swipes ORDER BY user_id"
        ).fetchall()
    assert decisions == [
        (first["user_id"], "heart"),
        (second["user_id"], "skip"),
    ]
    assert [topic for topic in topics if topic[1] == "movies"] == [
        (first["user_id"], "movies"),
        (first["user_id"], "movies"),
        (second["user_id"], "movies"),
    ]


def test_two_hearts_create_one_match_atomically(movie_api):
    client, _ = movie_api
    first, second = create_pair(client)
    movie = select_genre(client, first).json()["movie"]

    one_heart = swipe(client, first, movie["id"], "left")
    assert one_heart.status_code == 200
    assert one_heart.json()["status"] == "active"
    assert one_heart.json()["match"] is None

    match = swipe(client, second, movie["id"], "left")
    assert match.status_code == 200, match.text
    assert match.json()["status"] == "matched"
    assert match.json()["movie"] is None
    assert match.json()["match"] == movie
    assert state(client, first).json()["match"] == movie
    with sqlite3.connect(main.DB) as con:
        assert con.execute(
            "SELECT COUNT(*) FROM movie_rounds WHERE status='matched'"
        ).fetchone()[0] == 1


def test_duplicate_retry_is_idempotent_and_opposite_retry_conflicts(movie_api):
    client, topics = movie_api
    first, _ = create_pair(client)
    movie_id = select_genre(client, first).json()["movie"]["id"]

    original = swipe(client, first, movie_id, "left")
    duplicate = swipe(client, first, movie_id, "left")
    opposite = swipe(client, first, movie_id, "right")
    assert original.status_code == duplicate.status_code == 200
    assert duplicate.json()["round_id"] == original.json()["round_id"]
    assert duplicate.json()["swiped_count"] == 1
    assert opposite.status_code == 409
    assert [topic for topic in topics if topic[1] == "movies"] == [
        (first["user_id"], "movies"),
        (first["user_id"], "movies")
    ]
    with sqlite3.connect(main.DB) as con:
        assert con.execute("SELECT COUNT(*) FROM movie_swipes").fetchone()[0] == 1


def test_reset_starts_a_fresh_round(movie_api):
    client, topics = movie_api
    first, second = create_pair(client)
    old_state = select_genre(client, first).json()
    movie_id = old_state["movie"]["id"]
    assert swipe(client, first, movie_id, "left").status_code == 200
    assert swipe(client, second, movie_id, "left").json()["status"] == "matched"

    reset = client.post(
        "/movies/reset",
        json={"user_id": first["user_id"]},
        headers=headers(first),
    )
    assert reset.status_code == 200, reset.text
    fresh = reset.json()
    assert fresh["round_id"] != old_state["round_id"]
    assert fresh["status"] == "active"
    assert fresh["swiped_count"] == 0
    assert fresh["needs_genre"] is True
    assert fresh["genre_key"] is None
    assert fresh["movie"] is None
    assert fresh["match"] is None
    assert state(client, second).json()["round_id"] == fresh["round_id"]
    selected = select_genre(client, second).json()
    assert selected["movie"]["id"] != movie_id
    with sqlite3.connect(main.DB) as con:
        assert con.execute(
            "SELECT COUNT(*) FROM movie_rounds WHERE status='active'"
        ).fetchone()[0] == 1
    assert topics[-1] == (second["user_id"], "movies")


def test_init_db_does_not_persist_online_catalog(movie_api):
    _, _ = movie_api
    main.init_db()
    main.init_db()
    with sqlite3.connect(main.DB) as con:
        tables = {
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "movies" not in tables


def test_user_waits_after_catalog_until_partner_finishes(movie_api):
    client, _ = movie_api
    first, second = create_pair(client)
    selected = select_genre(client, first).json()
    assert selected["catalog_total"] == 2
    liked_movie_id = None

    while True:
        current = state(client, first).json()
        movie = current["movie"]
        if movie is None:
            break
        if liked_movie_id is None:
            liked_movie_id = movie["id"]
            direction = "left"
        else:
            direction = "right"
        assert swipe(client, first, movie["id"], direction).status_code == 200

    waiting = state(client, first).json()
    assert waiting["status"] == "active"
    assert waiting["movie"] is None
    assert waiting["match"] is None

    partner = state(client, second).json()
    assert partner["movie"]["id"] == liked_movie_id
    matched = swipe(client, second, liked_movie_id, "left").json()
    assert matched["status"] == "matched"
    assert matched["match"]["id"] == liked_movie_id
    assert state(client, first).json()["match"]["id"] == liked_movie_id


def test_genre_is_required_shared_and_filters_catalog(movie_api):
    client, topics = movie_api
    first, second = create_pair(client)
    initial = state(client, first).json()

    assert initial["needs_genre"] is True
    assert initial["genre_key"] is None
    assert initial["movie"] is None
    assert initial["catalog_total"] == 0
    assert any(g["key"] == "science-fiction" for g in initial["available_genres"])
    assert any(g["key"] == "horror" for g in initial["available_genres"])
    assert not {"thriller", "animation", "family", "music", "fantasy"} & {
        genre["key"] for genre in initial["available_genres"]
    }

    blocked = swipe(client, first, 1, "left")
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "Сначала выберите жанр фильма"

    selected = select_genre(client, first, "science-fiction")
    assert selected.status_code == 200, selected.text
    payload = selected.json()
    assert payload["needs_genre"] is False
    assert payload["genre_key"] == "science-fiction"
    assert "фантастика" in payload["movie"]["genres"]
    assert payload["catalog_total"] == next(
        g["movie_count"] for g in payload["available_genres"]
        if g["key"] == "science-fiction"
    )

    partner = state(client, second).json()
    assert partner["genre_key"] == "science-fiction"
    assert partner["movie"]["id"] == payload["movie"]["id"]
    assert select_genre(client, second, "science-fiction").status_code == 200
    conflict = select_genre(client, second, "comedy")
    assert conflict.status_code == 409
    assert topics[-1] == (first["user_id"], "movies")


def test_pending_genre_survives_repeated_init_db(movie_api):
    client, _ = movie_api
    first, _ = create_pair(client)
    pending = state(client, first).json()
    main.init_db()
    after_restart = state(client, first).json()
    assert after_restart["round_id"] == pending["round_id"]
    assert after_restart["genre_key"] is None
    assert after_restart["needs_genre"] is True


def test_legacy_local_catalog_rounds_are_cleared(tmp_path, monkeypatch):
    old_db = tmp_path / "legacy-movies.db"
    with sqlite3.connect(old_db) as con:
        con.execute(
            "CREATE TABLE movie_rounds("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "pair_low_id INTEGER NOT NULL,pair_high_id INTEGER NOT NULL,"
            "status TEXT NOT NULL,matched_movie_id INTEGER,created_at TEXT NOT NULL)"
        )
        con.execute(
            "INSERT INTO movie_rounds(pair_low_id,pair_high_id,status,created_at) "
            "VALUES(1,2,'active','2026-10-15T00:00:00')"
        )
    monkeypatch.setattr(main, "DB", str(old_db))

    main.init_db()

    with sqlite3.connect(old_db) as con:
        columns = [row[1] for row in con.execute("PRAGMA table_info(movie_rounds)")]
        rounds = con.execute("SELECT COUNT(*) FROM movie_rounds").fetchone()[0]
    assert "genre_key" in columns
    assert "catalog_source" in columns
    assert rounds == 0


def test_movie_poster_is_proxied_and_cached(monkeypatch):
    class Headers:
        @staticmethod
        def get_content_type():
            return "image/jpeg"

    class Upstream:
        headers = Headers()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        @staticmethod
        def read():
            return b"poster"

    monkeypatch.setattr(main, "urlopen", lambda request, timeout: Upstream())
    response = TestClient(main.app).get("/movies/poster/abc123.jpg")

    assert response.status_code == 200
    assert response.content == b"poster"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "public, max-age=86400"


def test_obsolete_genre_round_returns_to_catalog(movie_api):
    client, _ = movie_api
    first, second = create_pair(client)
    current = state(client, first).json()
    with sqlite3.connect(main.DB) as con:
        con.execute(
            "UPDATE movie_rounds SET genre_key='animation' WHERE id=?",
            (current["round_id"],),
        )
        con.execute(
            "INSERT INTO movie_swipes(round_id,user_id,movie_id,decision,created_at) "
            "VALUES(?,?,?,?,?)",
            (current["round_id"], first["user_id"], 101, "heart", "now"),
        )

    main.init_db()

    reset = state(client, second).json()
    assert reset["round_id"] == current["round_id"]
    assert reset["needs_genre"] is True
    assert reset["genre_key"] is None
    assert reset["swiped_count"] == 0


def test_each_round_has_a_new_stable_movie_order(movie_api):
    first = [movie["id"] for movie in main.movie_rows_for_genre(None, "all", 101)]
    repeated = [movie["id"] for movie in main.movie_rows_for_genre(None, "all", 101)]
    next_round = [movie["id"] for movie in main.movie_rows_for_genre(None, "all", 102)]

    assert repeated == first
    assert next_round != first
    assert set(next_round) == set(first)


def matches(client, user):
    return client.get(
        "/movies/matches", params={"user_id": user["user_id"]}, headers=headers(user)
    )


def watch(client, user, movie_id, watched):
    return client.post(
        "/movies/matches/watched",
        json={
            "user_id": user["user_id"],
            "movie_id": movie_id,
            "watched": watched,
        },
        headers=headers(user),
    )


def delete_match(client, user, movie_id):
    return client.delete(
        f"/movies/matches/{movie_id}",
        params={"user_id": user["user_id"]},
        headers=headers(user),
    )


def test_match_joins_shared_list_and_can_be_marked_watched(movie_api):
    client, topics = movie_api
    first, second = create_pair(client)
    movie = select_genre(client, first).json()["movie"]
    swipe(client, first, movie["id"], "left")
    assert swipe(client, second, movie["id"], "left").json()["status"] == "matched"

    listed = matches(client, first)
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["partner_name"] == "Sam"
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["watched"] is False
    assert item["movie"]["id"] == movie["id"]
    assert item["movie"]["title"] == movie["title"]

    partner_view = matches(client, second).json()
    assert [entry["movie"]["id"] for entry in partner_view["items"]] == [movie["id"]]

    marked = watch(client, second, movie["id"], True)
    assert marked.status_code == 200, marked.text
    assert marked.json()["items"][0]["watched"] is True
    assert matches(client, first).json()["items"][0]["watched"] is True
    with sqlite3.connect(main.DB) as con:
        watched, watched_at = con.execute(
            "SELECT watched,watched_at FROM movie_matches WHERE movie_id=?",
            (movie["id"],),
        ).fetchone()
    assert watched == 1
    assert watched_at

    unmarked = watch(client, first, movie["id"], False)
    assert unmarked.status_code == 200
    assert unmarked.json()["items"][0]["watched"] is False
    with sqlite3.connect(main.DB) as con:
        assert con.execute(
            "SELECT watched,watched_at FROM movie_matches WHERE movie_id=?",
            (movie["id"],),
        ).fetchone() == (0, "")
    assert topics[-1] == (first["user_id"], "movies")


def test_match_list_is_isolated_between_couples(movie_api):
    client, _ = movie_api
    first, second = create_pair(client)
    outsider, outsider_partner = create_pair(client, "Other", "Other partner")

    movie = select_genre(client, first).json()["movie"]
    swipe(client, first, movie["id"], "left")
    swipe(client, second, movie["id"], "left")

    outside = select_genre(client, outsider, "science-fiction").json()["movie"]
    swipe(client, outsider, outside["id"], "left")
    swipe(client, outsider_partner, outside["id"], "left")

    ids = [entry["movie"]["id"] for entry in matches(client, first).json()["items"]]
    assert ids == [movie["id"]]
    assert outside["id"] not in ids

    missing = watch(client, first, 999999, True)
    assert missing.status_code == 404


def test_match_can_be_deleted_for_both_partners(movie_api):
    client, topics = movie_api
    first, second = create_pair(client)
    movie = select_genre(client, first).json()["movie"]
    swipe(client, first, movie["id"], "left")
    swipe(client, second, movie["id"], "left")

    deleted = delete_match(client, first, movie["id"])
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["items"] == []
    assert matches(client, second).json()["items"] == []

    main.init_db()
    assert matches(client, first).json()["items"] == []
    assert delete_match(client, second, movie["id"]).status_code == 404
    assert topics[-1] == (first["user_id"], "movies")


def test_matches_backfill_from_existing_rounds(movie_api):
    client, _ = movie_api
    first, second = create_pair(client)
    movie = select_genre(client, first).json()["movie"]
    swipe(client, first, movie["id"], "left")
    swipe(client, second, movie["id"], "left")

    with sqlite3.connect(main.DB) as con:
        con.execute("DELETE FROM movie_matches")

    main.init_db()

    payload = matches(client, first).json()
    assert [entry["movie"]["id"] for entry in payload["items"]] == [movie["id"]]
    entry = payload["items"][0]
    assert entry["movie"]["title"] == movie["title"]
    assert entry["watched"] is False
