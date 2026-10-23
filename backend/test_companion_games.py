import copy
import base64
import pytest
from backend.companion_games import (
    act,
    buy_food,
    care_together,
    view,
)
from fastapi.testclient import TestClient
from backend import main


def state():
    return dict(coins=20, xp=0, joy=0.5, hunger=0.5, bond=0, sleeping=False)


def move(s, user, choice):
    g = s["playground"]["game"]
    return act(
        s,
        user,
        2 if user == 1 else 1,
        f'{g["id"]}:{g["revision"]}:{choice}',
        "2026-10-16",
    )


def test_choices_stay_secret_and_reward_only_once():
    s = state()
    act(s, 1, 2, "start:guess", "2026-10-16")
    move(s, 1, 2)
    public = view(s, 2)["game"]
    assert public["my_choice"] is None
    assert public["partner_answered"]
    assert "choices" not in public and "revealed" not in public
    with pytest.raises(ValueError):
        move(s, 1, 0)
    move(s, 2, 2)
    assert s["coins"] == 33
    assert len(view(s, 1)["game"]["revealed"]) == 2
    with pytest.raises(ValueError):
        move(s, 2, 2)
    assert s["coins"] == 33


@pytest.mark.parametrize("kind", ["catch", "adventure"])
def test_alternating_turns_and_stale_move_rejected(kind):
    s = state()
    act(s, 1, 2, f"start:{kind}", "2026-10-16")
    before = copy.deepcopy(s)
    with pytest.raises(ValueError):
        move(s, 2, 0)
    assert s == before
    g = s["playground"]["game"]
    stale = f'{g["id"]}:0:0'
    for i in range(6):
        move(s, i % 2 + 1, 0)
    assert g["status"] == "finished"
    assert len(s["playground"]["album"]) == 1
    with pytest.raises(ValueError):
        act(s, 1, 2, stale, "2026-10-16")


def test_daily_care_needs_both_and_is_idempotent():
    s = state()
    for _ in range(3):
        care_together(s, 1, "2026-10-16")
    assert s["coins"] == 20
    care_together(s, 2, "2026-10-16")
    care_together(s, 2, "2026-10-16")
    assert s["coins"] == 35


def test_reward_cap_resets_next_day():
    s = state()
    for _ in range(4):
        act(s, 1, 2, "start:guess", "2026-10-16")
        move(s, 1, 0)
        move(s, 2, 0)
    assert s["coins"] == 59
    assert s["playground"]["game"]["reward"] == 0
    act(s, 1, 2, "start:guess", "2026-10-17")
    g = s["playground"]["game"]
    act(s, 1, 2, f'{g["id"]}:0:0', "2026-10-17")
    act(s, 2, 1, f'{g["id"]}:0:0', "2026-10-17")
    assert s["coins"] == 72


def test_doodle_realtime_protocol_is_private_authorized_and_rewarded_once():
    s = state()
    act(s, 1, 2, "start:doodle", "2026-10-16")
    game = s["playground"]["game"]
    game_id = game["id"]

    drawer = view(s, 1)["game"]
    guesser = view(s, 2)["game"]
    assert drawer["role"] == "drawer" and guesser["role"] == "guesser"
    assert drawer["drawer"] == 1 and drawer["guesser"] == 2
    assert drawer["word"] and drawer["word_en"]
    assert "word" not in guesser and "word_en" not in guesser
    assert "target_index" not in drawer and "target_index" not in guesser

    with pytest.raises(ValueError, match="только художник"):
        act(s, 2, 1, f"{game_id}:0:stroke:1,2;3,4", "2026-10-16")
    assert game["revision"] == 0
    assert act(s, 1, 2, f"{game_id}:0:stroke:1,2;1000,0", "2026-10-16") == "Штрих добавлен"
    assert view(s, 2)["game"]["strokes"] == [[[1, 2], [1000, 0]]]

    with pytest.raises(ValueError, match="обновите экран"):
        act(s, 1, 2, f"{game_id}:0:clear", "2026-10-16")
    with pytest.raises(ValueError, match="только партнёр"):
        act(s, 1, 2, f"{game_id}:1:guess:Y2F0", "2026-10-16")

    wrong = base64.urlsafe_b64encode("не знаю!".encode()).decode().rstrip("=")
    assert "Попробуйте" in act(
        s, 2, 1, f"{game_id}:1:guess:{wrong}", "2026-10-16"
    )
    assert game["revision"] == 2 and game["guesses"] == ["не знаю!"]

    answer = f"  {drawer['word_en'].upper()}!!!  "
    encoded = base64.urlsafe_b64encode(answer.encode()).decode().rstrip("=")
    assert "Слово угадано" in act(
        s, 2, 1, f"{game_id}:2:guess:{encoded}", "2026-10-16"
    )
    assert game["status"] == "finished" and game["score"] == 9
    assert game["reward"] == 19 and s["coins"] == 39
    assert len(s["playground"]["album"]) == 1
    assert view(s, 2)["game"]["word"] == drawer["word"]
    with pytest.raises(ValueError):
        act(s, 2, 1, f"{game_id}:2:guess:{encoded}", "2026-10-16")
    assert s["coins"] == 39 and len(s["playground"]["album"]) == 1


def test_doodle_giveup_and_invalid_strokes_do_not_reward():
    s = state()
    act(s, 1, 2, "start:doodle", "2026-10-16")
    game = s["playground"]["game"]
    game_id = game["id"]

    for payload in ("", "1,2;nope", "-1,2", "1001,0"):
        with pytest.raises(ValueError):
            act(s, 1, 2, f"{game_id}:0:stroke:{payload}", "2026-10-16")
    too_many = ";".join("1,1" for _ in range(201))
    with pytest.raises(ValueError, match="Слишком много точек"):
        act(s, 1, 2, f"{game_id}:0:stroke:{too_many}", "2026-10-16")
    assert game["strokes"] == [] and game["revision"] == 0

    assert act(s, 2, 1, f"{game_id}:0:giveup", "2026-10-16") == "Игра завершена без награды"
    assert game["status"] == "finished"
    assert game["score"] == game["reward"] == 0
    assert s["coins"] == 20 and "album" not in s["playground"]


def test_legacy_doodle_round_is_hidden_and_can_be_restarted():
    s = state()
    s["playground"] = {
        "game": {
            "id": "legacy",
            "revision": 0,
            "kind": "doodle",
            "status": "active",
            "starter": 1,
            "choices": {},
        }
    }

    assert "game" not in view(s, 1)
    act(s, 1, 2, "start:doodle", "2026-10-16")
    assert s["playground"]["game"]["id"] != "legacy"
    assert view(s, 1)["game"]["role"] == "drawer"


def test_solo_clouds_rewards_by_score_and_caps_daily():
    s = state()
    assert "+17 монет" in act(s, 1, 2, "solo:clouds:7", "2026-10-16")
    assert s["coins"] == 37
    act(s, 1, 2, "solo:clouds:99", "2026-10-16")
    assert s["coins"] == 67
    act(s, 1, 2, "solo:clouds:20", "2026-10-16")
    assert s["coins"] == 97
    assert "обновятся" in act(s, 1, 2, "solo:clouds:20", "2026-10-16")
    assert s["coins"] == 97
    assert s["playground"]["album"][-1]["kind"] == "clouds"
    with pytest.raises(ValueError):
        act(s, 1, 2, "solo:unknown:1", "2026-10-16")


def test_solo_cloud_records_are_personal_visible_and_never_decrease():
    s = state()
    act(s, 1, 2, "solo:clouds:7:420", "2026-10-16")
    act(s, 1, 2, "solo:clouds:5:300", "2026-10-16")
    assert view(s, 1)["cloud_best"] == 420
    assert view(s, 1)["partner_cloud_best"] == 0
    assert view(s, 2)["cloud_best"] == 0
    assert view(s, 2)["partner_cloud_best"] == 420

    act(s, 2, 1, "solo:clouds:9:510", "2026-10-16")
    assert view(s, 1)["partner_cloud_best"] == 510
    assert view(s, 2)["cloud_best"] == 510
    assert "cloud_bests" not in view(s, 1)
    with pytest.raises(ValueError, match="Неверный рекорд"):
        act(s, 1, 2, "solo:clouds:3:100001", "2026-10-16")


def test_rooms_have_no_choices_and_kitchen_has_food_shop():
    s = state()
    rooms = view(s, 1, "2026-10-16")["rooms"]
    assert set(rooms) == {"playroom", "kitchen", "bathroom", "bedroom", "travel"}
    assert "choices" not in rooms["playroom"]
    assert rooms["playroom"]["foods"] == []
    assert [food["key"] for food in rooms["kitchen"]["foods"]] == [
        "meal",
        "treat",
        "milk",
    ]


def test_buy_food_spends_coins_and_feeds_immediately():
    s = state()
    message = buy_food(s, "treat")
    assert message == "Лакомство куплено за 8 монет"
    assert s["coins"] == 12
    assert s["hunger"] == pytest.approx(0.62)
    assert s["joy"] == pytest.approx(0.59)

    s["coins"] = 2
    before = copy.deepcopy(s)
    with pytest.raises(ValueError, match="Нужно ещё 3 монет"):
        buy_food(s, "meal")
    assert s == before

    with pytest.raises(ValueError, match="Еда не найдена"):
        buy_food(s, "unknown")


def test_sleep_restores_energy_and_wake_is_shared_state():
    now = 10_000
    companion = main.fresh_companion()
    companion.update(adopted=True, energy=0.4, timestamp=now)

    sleeping, message, animation = main.companion_care(
        companion, "sleep", now + 3_000
    )
    assert sleeping["sleeping"] is True
    assert animation == "sleep"
    assert "энергия" in message

    rested = main.companion_advance(sleeping, now + 3_000 + 3_600_000)
    assert rested["energy"] == pytest.approx(0.8, abs=0.001)

    awake, _, animation = main.companion_care(
        rested, "sleep", now + 6_000 + 3_600_000
    )
    assert awake["sleeping"] is False
    assert animation == "love"


def test_pair_api_persists_secret_choices_and_isolates_couples(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "pet.db"))
    main.init_db()
    client = TestClient(main.app)
    first = client.post("/pair", json={"name": "Alex"}).json()
    second = client.post(
        "/pair/join", json={"name": "Sam", "code": first["pair_code"]}
    ).json()

    def post(user, path, **fields):
        return client.post(
            path,
            json={"user_id": user["user_id"], **fields},
            headers={"X-Auth-Token": user["token"]},
        )

    assert (
        post(first, "/companion/propose", type="PET", name="Mochi").status_code == 200
    )
    assert post(second, "/companion/confirm").status_code == 200
    started = post(
        first, "/companion/action", action="game", value="start:guess"
    ).json()
    game_id = started["state"]["playground"]["game"]["id"]
    assert (
        post(
            first, "/companion/action", action="game", value=f"{game_id}:0:2"
        ).status_code
        == 200
    )
    snapshot = client.get(
        "/companion",
        params={"user_id": second["user_id"]},
        headers={"X-Auth-Token": second["token"]},
    ).json()
    game = snapshot["state"]["playground"]["game"]
    assert game["partner_answered"] and game["my_choice"] is None
    assert "choices" not in game and "revealed" not in game
    result = post(
        second, "/companion/action", action="game", value=f"{game_id}:0:2"
    ).json()
    assert result["state"]["coins"] == 33
    assert result["state"]["playground"]["game"]["status"] == "finished"
    kitchen = snapshot["state"]["playground"]["rooms"]["kitchen"]
    assert "choices" not in kitchen
    assert len(kitchen["foods"]) == 3
    food_result = post(
        first, "/companion/action", action="buy_food", value="milk"
    ).json()
    assert food_result["state"]["coins"] == 21
    assert food_result["state"]["hunger"] > 0.9
    assert food_result["animation"] == "feed"
    assert (
        post(
            first, "/companion/action", action="room_activity", value="travel:2"
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/daily",
            params={"user_id": first["user_id"]},
            headers={"X-Auth-Token": first["token"]},
        ).status_code
        == 200
    )
    assert post(first, "/daily/answer", text="Первый ответ").status_code == 200
    assert post(second, "/daily/answer", text="Второй ответ").status_code == 200
    rewarded = client.get(
        "/companion",
        params={"user_id": first["user_id"]},
        headers={"X-Auth-Token": first["token"]},
    ).json()
    assert rewarded["state"]["coins"] == 26
    outsider = client.post("/pair", json={"name": "Other"}).json()
    client.post(
        "/pair/join", json={"name": "Other partner", "code": outsider["pair_code"]}
    )
    assert (
        post(
            outsider, "/companion/action", action="game", value=f"{game_id}:0:2"
        ).status_code
        == 409
    )
