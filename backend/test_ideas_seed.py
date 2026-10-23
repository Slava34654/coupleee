import os
import tempfile


test_db = os.path.join(tempfile.gettempdir(), "enrwine_ideas_seed_test.db")
if os.path.exists(test_db):
    os.remove(test_db)
os.environ["COUPLE_DB"] = test_db

import main


main.init_db()
main.init_db()
connection = main.db()
rows = connection.execute("SELECT title,category,budget FROM ideas").fetchall()
connection.close()
ideas = {tuple(row) for row in rows}

assert len(rows) == 18, len(rows)
assert (
    "Закат на самой высокой точке города",
    "Прогулка / Романтика",
    "Бесплатно",
) in ideas
assert (
    "Рисуем портреты друг друга",
    "Творчество / Юмор",
    "Дёшево",
) in ideas

print("ideas seed OK:", len(rows))
