import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def quiz_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "quiz-result.db"))
    main.init_db()
    return TestClient(main.app)


def create_pair(client):
    first = client.post("/pair", json={"name": "Alex"}).json()
    second = client.post(
        "/pair/join", json={"name": "Sam", "code": first["pair_code"]}
    ).json()
    return first, second


def headers(user):
    return {"X-Auth-Token": user["token"]}


def test_compatibility_hidden_until_both_finish(quiz_api):
    client = quiz_api
    first, second = create_pair(client)
    quiz_id = client.get("/quizzes").json()[0]["id"]
    questions = client.get(
        f"/quiz/{quiz_id}",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()["questions"]
    assert len(questions) == 10

    empty = client.get(
        f"/quiz/{quiz_id}/result",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()
    assert empty["compatibility"] is None
    assert empty["completed"] is False
    assert empty["details"] == []

    for index, question in enumerate(questions[:5]):
        client.post(
            f"/quiz/{quiz_id}/answer",
            json={
                "user_id": first["user_id"],
                "qid": question["id"],
                "option": 0,
            },
            headers=headers(first),
        )
        client.post(
            f"/quiz/{quiz_id}/answer",
            json={
                "user_id": second["user_id"],
                "qid": question["id"],
                "option": 0 if index < 3 else 1,
            },
            headers=headers(second),
        )

    partial = client.get(
        f"/quiz/{quiz_id}/result",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()
    assert partial["compatibility"] is None
    assert partial["completed"] is False
    assert partial["details"] == []
    assert partial["answered_together"] == 5


def test_completed_result_has_match_details(quiz_api):
    client = quiz_api
    first, second = create_pair(client)
    quiz_id = client.get("/quizzes").json()[0]["id"]
    questions = client.get(
        f"/quiz/{quiz_id}",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()["questions"]

    for index, question in enumerate(questions):
        client.post(
            f"/quiz/{quiz_id}/answer",
            json={
                "user_id": first["user_id"],
                "qid": question["id"],
                "option": 0,
            },
            headers=headers(first),
        )
        client.post(
            f"/quiz/{quiz_id}/answer",
            json={
                "user_id": second["user_id"],
                "qid": question["id"],
                "option": 0 if index < 6 else 1,
            },
            headers=headers(second),
        )

    result = client.get(
        f"/quiz/{quiz_id}/result",
        params={"user_id": first["user_id"]},
        headers=headers(first),
    ).json()
    assert result["completed"] is True
    assert result["compatibility"] == 60
    assert result["answered_together"] == 10
    assert len(result["details"]) == 10
    matched = [item for item in result["details"] if item["matched"]]
    assert len(matched) == 6
    for item in result["details"]:
        assert item["question"]
        assert item["my_answer"]
        assert item["partner_answer"]
        assert item["matched"] == (item["my_option"] == item["partner_option"])
