import json
import os
import tempfile
import uuid

os.environ["COUPLE_DB"] = os.path.join(
    tempfile.gettempdir(), f"enrwine-quiz-{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient

from backend.main import app, db, init_db
from backend.quiz_catalog import QUIZ_CATEGORIES, generated_questions


def test_quiz_catalog_content_is_valid_and_unique():
    questions = [
        question
        for category in QUIZ_CATEGORIES
        for subtopic in category["subtopics"]
        for question in generated_questions(subtopic)
    ]
    normalized_texts = [question["text"].strip().casefold() for question in questions]

    assert len(questions) == 1000
    assert len(normalized_texts) == len(set(normalized_texts))
    assert all(question["text"].strip() for question in questions)
    assert all(
        len(question["options"]) == 4
        and len(set(question["options"])) == len(question["options"])
        and all(option.strip() for option in question["options"])
        for question in questions
    )


def test_quiz_hierarchy_is_complete_and_idempotent():
    with TestClient(app) as client:
        categories = client.get("/quiz-categories").json()
        assert len(categories) == 10
        assert all(item["subtopics"] == 10 for item in categories)
        assert all(item["questions"] == 100 for item in categories)

        for category in categories:
            detail = client.get(
                f"/quiz-categories/{category['id']}/subtopics").json()
            assert detail["title"] == category["title"]
            assert len(detail["subtopics"]) == 10
            assert all(item["questions"] == 10 for item in detail["subtopics"])

        quizzes = client.get("/quizzes").json()
        assert len(quizzes) == 100
        assert all(item["questions"] == 10 for item in quizzes)

        connection = db()
        before = connection.execute(
            "SELECT id,seed_key FROM quiz_q ORDER BY id").fetchall()
        connection.close()
        init_db()
        connection = db()
        after = connection.execute(
            "SELECT id,seed_key FROM quiz_q ORDER BY id").fetchall()
        connection.close()
        assert [(row["id"], row["seed_key"]) for row in after] == [
            (row["id"], row["seed_key"]) for row in before]


def test_quiz_seed_refreshes_content_without_changing_question_id():
    init_db()
    connection = db()
    original = connection.execute(
        "SELECT id FROM quiz_q WHERE seed_key=?", ("compatibility:0:q0",)
    ).fetchone()
    connection.execute(
        "UPDATE quiz_q SET text=?,options=? WHERE id=?",
        ("Устаревший вопрос", '["старый ответ"]', original["id"]),
    )
    connection.commit()
    connection.close()

    init_db()
    connection = db()
    refreshed = connection.execute(
        "SELECT id,text,options FROM quiz_q WHERE seed_key=?",
        ("compatibility:0:q0",),
    ).fetchone()
    connection.close()
    expected = generated_questions("Насколько вы совпадаете?")[0]

    assert refreshed["id"] == original["id"]
    assert refreshed["text"] == expected["text"]
    assert refreshed["options"] == json.dumps(expected["options"], ensure_ascii=False)


def test_removed_seeded_subtopic_and_answers_are_cleaned_up():
    init_db()
    connection = db()
    category_id = connection.execute(
        "SELECT id FROM quiz_categories WHERE seed_key='compatibility'"
    ).fetchone()["id"]
    quiz_id = connection.execute(
        "INSERT INTO quizzes(title,category_id,seed_key,position) VALUES(?,?,?,?)",
        ("Удалённая подтема", category_id, "compatibility:10", 10),
    ).lastrowid
    question_id = connection.execute(
        "INSERT INTO quiz_q(quiz_id,text,options,seed_key,position) VALUES(?,?,?,?,?)",
        (quiz_id, "Удалённый вопрос", '["A","B"]', "compatibility:10:q0", 0),
    ).lastrowid
    connection.execute(
        "INSERT INTO quiz_a(user_id,quiz_id,qid,option) VALUES(?,?,?,?)",
        (999, quiz_id, question_id, 0),
    )
    connection.commit()
    connection.close()

    init_db()
    connection = db()
    assert connection.execute(
        "SELECT 1 FROM quizzes WHERE id=?", (quiz_id,)
    ).fetchone() is None
    assert connection.execute(
        "SELECT 1 FROM quiz_q WHERE id=?", (question_id,)
    ).fetchone() is None
    assert connection.execute(
        "SELECT 1 FROM quiz_a WHERE quiz_id=?", (quiz_id,)
    ).fetchone() is None
    connection.close()
