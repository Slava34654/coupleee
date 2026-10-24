import json
import sqlite3


def connect(path: str):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(
    path,
    *,
    upgrade,
    movie_genres,
    quiz_categories,
    generated_questions,
    ideas,
    packs,
    sql_placeholders,
    backfill_movie_matches,
):
    upgrade(path)
    con = connect(path)
    c = con.cursor()
    valid_genres = tuple(movie_genres)
    placeholders = sql_placeholders(len(valid_genres))
    obsolete_rounds = c.execute(
        "SELECT id FROM movie_rounds WHERE id IN ("
        "SELECT MAX(id) FROM movie_rounds GROUP BY pair_low_id,pair_high_id"
        ") AND genre_key IS NOT NULL AND genre_key NOT IN (" + placeholders + ")",
        valid_genres,
    ).fetchall()
    for round_row in obsolete_rounds:
        c.execute("DELETE FROM movie_swipes WHERE round_id=?", (round_row["id"],))
        c.execute(
            "UPDATE movie_rounds SET status='active',matched_movie_id=NULL,"
            "genre_key=NULL WHERE id=?",
            (round_row["id"],),
        )
    backfill_movie_matches(c)
    for category_position, category in enumerate(quiz_categories):
        category_row = c.execute(
            "SELECT id FROM quiz_categories WHERE seed_key=?", (category["key"],)
        ).fetchone()
        if category_row:
            category_id = category_row["id"]
            c.execute(
                "UPDATE quiz_categories SET title=?,position=? WHERE id=?",
                (category["title"], category_position, category_id),
            )
        else:
            category_id = c.execute(
                "INSERT INTO quiz_categories(seed_key,title,position) VALUES(?,?,?)",
                (category["key"], category["title"], category_position),
            ).lastrowid
        for quiz_position, title in enumerate(category["subtopics"]):
            quiz_key = f'{category["key"]}:{quiz_position}'
            quiz_row = c.execute(
                "SELECT id FROM quizzes WHERE seed_key=?", (quiz_key,)
            ).fetchone()
            if not quiz_row:
                quiz_row = c.execute(
                    "SELECT id FROM quizzes WHERE title=? ORDER BY id LIMIT 1", (title,)
                ).fetchone()
            if quiz_row:
                quiz_id = quiz_row["id"]
                c.execute(
                    "UPDATE quizzes SET title=?,category_id=?,seed_key=?,position=? WHERE id=?",
                    (title, category_id, quiz_key, quiz_position, quiz_id),
                )
            else:
                quiz_id = c.execute(
                    "INSERT INTO quizzes(title,category_id,seed_key,position) VALUES(?,?,?,?)",
                    (title, category_id, quiz_key, quiz_position),
                ).lastrowid
            questions = generated_questions(title)
            for question_position, question in enumerate(questions):
                question_key = f"{quiz_key}:q{question_position}"
                question_row = c.execute(
                    "SELECT id FROM quiz_q WHERE seed_key=?", (question_key,)
                ).fetchone()
                if not question_row:
                    question_row = c.execute(
                        "SELECT id FROM quiz_q WHERE quiz_id=? AND text=? ORDER BY id LIMIT 1",
                        (quiz_id, question["text"]),
                    ).fetchone()
                if question_row:
                    c.execute(
                        "UPDATE quiz_q SET text=?,options=?,seed_key=?,position=? WHERE id=?",
                        (
                            question["text"],
                            json.dumps(question["options"], ensure_ascii=False),
                            question_key,
                            question_position,
                            question_row["id"],
                        ),
                    )
                else:
                    c.execute(
                        "INSERT INTO quiz_q(quiz_id,text,options,seed_key,position) VALUES(?,?,?,?,?)",
                        (
                            quiz_id,
                            question["text"],
                            json.dumps(question["options"], ensure_ascii=False),
                            question_key,
                            question_position,
                        ),
                    )
            stale_questions = c.execute(
                "SELECT id FROM quiz_q WHERE quiz_id=? AND position>=? AND seed_key LIKE ?",
                (quiz_id, len(questions), f"{quiz_key}:q%"),
            ).fetchall()
            for stale_question in stale_questions:
                c.execute("DELETE FROM quiz_a WHERE qid=?", (stale_question["id"],))
                c.execute("DELETE FROM quiz_q WHERE id=?", (stale_question["id"],))
    valid_quiz_keys = [
        f'{category["key"]}:{position}'
        for category in quiz_categories
        for position in range(len(category["subtopics"]))
    ]
    valid_placeholders = sql_placeholders(len(valid_quiz_keys))
    stale_quizzes = c.execute(
        "SELECT id FROM quizzes WHERE seed_key IS NOT NULL "
        "AND seed_key NOT IN (" + valid_placeholders + ")",
        valid_quiz_keys,
    ).fetchall()
    for stale_quiz in stale_quizzes:
        c.execute("DELETE FROM quiz_a WHERE quiz_id=?", (stale_quiz["id"],))
        c.execute("DELETE FROM quiz_q WHERE quiz_id=?", (stale_quiz["id"],))
        c.execute("DELETE FROM quizzes WHERE id=?", (stale_quiz["id"],))
    for title, category, budget in ideas:
        c.execute(
            "INSERT INTO ideas(title,category,budget) "
            "SELECT ?,?,? WHERE NOT EXISTS(SELECT 1 FROM ideas WHERE title=?)",
            (title, category, budget, title),
        )
    for pack in packs:
        row = c.execute(
            "SELECT id FROM packs WHERE title=?", (pack["title"],)
        ).fetchone()
        if row:
            c.execute("UPDATE packs SET kind=? WHERE id=?", (pack["kind"], row["id"]))
            continue
        pack_id = c.execute(
            "INSERT INTO packs(title,description,kind) VALUES(?,?,?)",
            (pack["title"], pack["description"], pack["kind"]),
        ).lastrowid
        c.executemany(
            "INSERT INTO pack_q(pack_id,text) VALUES(?,?)",
            [(pack_id, text) for text in pack["questions"]],
        )
    con.commit()
    con.close()
