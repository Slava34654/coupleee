"""Server-authoritative, asynchronous cooperative companion games."""

import copy
import base64
import binascii
import secrets
import unicodedata


DOODLE_WORDS = (
    ("кот", "cat", ("котик", "кошка", "kitty")),
    ("дом", "house", ("домик", "home")),
    ("солнце", "sun", ("солнышко",)),
    ("дерево", "tree", ()),
    ("рыба", "fish", ("рыбка",)),
    ("цветок", "flower", ("цветочек",)),
    ("сердце", "heart", ("сердечко",)),
    ("машина", "car", ("автомобиль",)),
    ("звезда", "star", ("звездочка", "звёздочка")),
    ("зонт", "umbrella", ("зонтик",)),
)
DOODLE_MAX_POINTS = 200
DOODLE_MAX_STROKES = 100


def view(state, user_id, day=None):
    result = copy.deepcopy(state.get("playground", {}))
    cloud_bests = result.pop("cloud_bests", {})
    result["cloud_best"] = int(cloud_bests.get(str(user_id), 0))
    result["partner_cloud_best"] = max(
        (int(score) for owner, score in cloud_bests.items() if owner != str(user_id)),
        default=0,
    )
    game = result.get("game")
    if game:
        if game.get("kind") == "doodle":
            if "target_index" not in game:
                result.pop("game", None)
                result["rooms"] = room_view(state, user_id, day)
                return result
            target_index = game.pop("target_index")
            game["role"] = (
                "drawer" if user_id == game["drawer"] else "guesser"
            )
            if game["status"] == "finished" or game["role"] == "drawer":
                game["word"], game["word_en"], _ = DOODLE_WORDS[target_index]
        else:
            choices = game.pop("choices", {})
            game["my_choice"] = choices.get(str(user_id))
            game["partner_answered"] = any(
                key != str(user_id) for key in choices
            )
            if game["status"] == "finished":
                game["revealed"] = choices
    result["rooms"] = room_view(state, user_id, day)
    return result


def care_together(state, user_id, day):
    playground = state.setdefault("playground", {})
    if playground.get("care_day") != day:
        playground.update(care_day=day, carers=[], care_rewarded=False)
    playground["carers"] = list(set(playground["carers"]) | {user_id})
    if len(playground["carers"]) == 2 and not playground["care_rewarded"]:
        playground["care_rewarded"] = True
        state["coins"] += 15
        state["bond"] = min(100, state["bond"] + 2)
        return "Вы оба позаботились о питомце! +15 монет"
    return ""


def act(state, user_id, partner_id, value, day):
    """Every move carries its game ID and revision to reject replayed requests."""
    playground = state.setdefault("playground", {})
    parts = value.split(":")
    game = playground.get("game")
    if game and game.get("kind") == "doodle" and "target_index" not in game:
        game["status"] = "finished"
    if parts[0] == "solo":
        if len(parts) not in (3, 4) or parts[1] != "clouds":
            raise ValueError("Неизвестная игра")
        if state.get("sleeping"):
            raise ValueError("Сначала разбудите питомца")
        try:
            score = int(parts[2])
        except ValueError:
            raise ValueError("Неверный результат")
        score = max(0, min(20, score))
        if len(parts) == 4:
            try:
                height = int(parts[3])
            except ValueError:
                raise ValueError("Неверный рекорд")
            if not 0 <= height <= 100_000:
                raise ValueError("Неверный рекорд")
            cloud_bests = playground.setdefault("cloud_bests", {})
            owner = str(user_id)
            cloud_bests[owner] = max(int(cloud_bests.get(owner, 0)), height)
        reward = _reward(
            state, playground, day, "clouds", score, "solo_rewards", "solo_reward_day"
        )
        return (
            f"Прыжки по облакам! +{reward} монет"
            if reward
            else "Прыжки по облакам! Награды обновятся завтра"
        )
    if parts[0] == "start":
        if len(parts) != 2 or parts[1] not in ("catch", "guess", "doodle", "adventure"):
            raise ValueError("Неизвестная игра")
        if game and game["status"] == "active":
            raise ValueError("Сначала завершите текущую игру вдвоём")
        if state.get("sleeping"):
            raise ValueError("Сначала разбудите питомца")
        if parts[1] == "doodle":
            game = dict(
                id=secrets.token_hex(8),
                revision=0,
                kind="doodle",
                status="active",
                drawer=user_id,
                guesser=partner_id,
                target_index=secrets.randbelow(len(DOODLE_WORDS)),
                strokes=[],
                guesses=[],
                score=0,
            )
        else:
            game = dict(
                id=secrets.token_hex(8),
                revision=0,
                kind=parts[1],
                status="active",
                turn=user_id,
                starter=user_id,
                step=0,
                score=0,
                choices={},
                story=[],
                target=secrets.randbelow(3),
            )
        playground["game"] = game
        return "Игра началась! Партнёр может присоединиться в любое время"
    if game and game.get("kind") == "doodle":
        return _doodle_act(state, playground, game, user_id, value, day)
    if not game or game["status"] != "active" or len(parts) != 3:
        raise ValueError("Обновите игру")
    if parts[0] != game["id"] or parts[1] != str(game["revision"]):
        raise ValueError("Ход уже изменился — обновите экран")
    choice = int(parts[2])
    if choice not in (0, 1, 2):
        raise ValueError("Неверный выбор")
    kind = game["kind"]
    if kind in ("guess", "doodle"):
        key = str(user_id)
        if key in game["choices"]:
            raise ValueError("Ваш выбор уже сохранён")
        game["choices"][key] = choice
        # Keep revision stable until both secret choices have arrived.
        if len(game["choices"]) < 2:
            return "Ваш выбор скрыт. Ждём партнёра"
        game["score"] = 3 if len(set(game["choices"].values())) == 1 else 1
        game["status"] = "finished"
    else:
        if game["turn"] != user_id:
            raise ValueError("Сейчас ход партнёра")
        if kind == "catch":
            if game["step"] % 2 == 0:
                game["aim"] = choice
                game["story"].append(
                    "Направление выбрано. Партнёр выбирает силу прыжка"
                )
            else:
                caught = (game["aim"] + choice) % 3 == game["target"]
                game["score"] += int(caught)
                game["story"].append(
                    "Угощение поймано! 🐾" if caught else "Почти! Попробуем ещё"
                )
                game["target"] = secrets.randbelow(3)
        else:
            events = (
                "Сад светлячков",
                "Мост над ручьём",
                "Лесная поляна",
                "Домик совы",
                "Звёздная тропа",
                "Сундук воспоминаний",
            )
            game["story"].append(
                f'{events[game["step"]]}: '
                + ("нашли кристалл", "помогли лесному другу", "сделали привал")[choice]
            )
            game["score"] += (2, 3, 1)[choice]
        game["step"] += 1
        game["turn"] = partner_id
        game["revision"] += 1
        if game["step"] >= 6:
            game["status"] = "finished"
    if game["status"] != "finished":
        return "Ход передан партнёру"
    reward = _reward(state, playground, day, kind, game["score"])
    game["reward"] = reward
    return (
        f"Вы справились вместе! +{reward} монет"
        if reward
        else "Отличная игра! Награды обновятся завтра"
    )


def _doodle_act(state, playground, game, user_id, value, day):
    if game["status"] != "active":
        raise ValueError("Обновите игру")
    parts = value.split(":")
    if len(parts) not in (3, 4):
        raise ValueError("Неверная команда рисунка")
    if parts[0] != game["id"] or parts[1] != str(game["revision"]):
        raise ValueError("Ход уже изменился — обновите экран")

    action = parts[2]
    payload = parts[3] if len(parts) == 4 else None
    if action == "stroke":
        if user_id != game["drawer"]:
            raise ValueError("Рисовать может только художник")
        if not payload:
            raise ValueError("Штрих не может быть пустым")
        raw_points = payload.split(";")
        if len(raw_points) > DOODLE_MAX_POINTS:
            raise ValueError("Слишком много точек в штрихе")
        points = []
        try:
            for raw_point in raw_points:
                coordinates = raw_point.split(",")
                if len(coordinates) != 2:
                    raise ValueError
                point = [int(coordinates[0]), int(coordinates[1])]
                if not all(0 <= coordinate <= 1000 for coordinate in point):
                    raise ValueError
                points.append(point)
        except (TypeError, ValueError):
            raise ValueError("Неверные точки штриха")
        if len(game["strokes"]) >= DOODLE_MAX_STROKES:
            raise ValueError("Слишком много штрихов")
        game["strokes"].append(points)
        game["revision"] += 1
        return "Штрих добавлен"

    if action == "clear":
        if user_id != game["drawer"]:
            raise ValueError("Очистить рисунок может только художник")
        if payload is not None:
            raise ValueError("Неверная команда очистки")
        game["strokes"] = []
        game["revision"] += 1
        return "Рисунок очищен"

    if action == "guess":
        if user_id != game["guesser"]:
            raise ValueError("Угадывать может только партнёр")
        guess = _decode_doodle_guess(payload)
        normalized = _normalize_doodle_word(guess)
        if not normalized:
            raise ValueError("Ответ не может быть пустым")
        game["guesses"].append(guess.strip())
        word, word_en, aliases = DOODLE_WORDS[game["target_index"]]
        answers = (word, word_en, *aliases)
        if normalized not in {_normalize_doodle_word(answer) for answer in answers}:
            game["revision"] += 1
            return "Пока не угадано. Попробуйте ещё"
        wrong_guesses = len(game["guesses"]) - 1
        game["score"] = max(1, 10 - wrong_guesses)
        game["status"] = "finished"
        game["reward"] = _reward(
            state, playground, day, "doodle", game["score"]
        )
        return (
            f'Слово угадано! +{game["reward"]} монет'
            if game["reward"]
            else "Слово угадано! Награды обновятся завтра"
        )

    if action == "giveup":
        if user_id not in (game["drawer"], game["guesser"]):
            raise ValueError("Вы не участвуете в этой игре")
        if payload is not None:
            raise ValueError("Неверная команда сдачи")
        game.update(status="finished", score=0, reward=0)
        return "Игра завершена без награды"

    raise ValueError("Неизвестное действие рисунка")


def _decode_doodle_guess(payload):
    if not payload:
        raise ValueError("Ответ не может быть пустым")
    try:
        encoded = payload.encode("ascii")
        encoded += b"=" * (-len(encoded) % 4)
        return base64.b64decode(encoded, altchars=b"-_", validate=True).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, ValueError):
        raise ValueError("Неверный формат ответа")


def _normalize_doodle_word(value):
    value = value.casefold().replace("ё", "е")
    return " ".join(
        "".join(
            character if unicodedata.category(character)[0] in ("L", "N") else " "
            for character in value
        ).split()
    )


def _reward(state, playground, day, kind, score, cap="rewards", cap_day="reward_day"):
    if playground.get(cap_day) != day:
        playground.update({cap_day: day, cap: 0})
    reward = 10 + score if playground[cap] < 3 else 0
    playground[cap] += 1
    state["coins"] += reward
    state["xp"] += 15 if reward else 0
    state["joy"] = min(1, state["joy"] + 0.1)
    state["bond"] = min(100, state["bond"] + (2 if reward else 0))
    playground["completed"] = playground.get("completed", 0) + 1
    badges = playground.setdefault("badges", [])
    for count, badge in (
        (1, "Первое приключение"),
        (3, "Дружная команда"),
        (10, "Лучшие друзья"),
    ):
        if playground["completed"] >= count and badge not in badges:
            badges.append(badge)
    if playground["completed"] == 3:
        state["accessory"] = "bow"
    if playground["completed"] == 10:
        state["accessory"] = "crown"
    album = playground.setdefault("album", [])
    album.append(dict(day=day, kind=kind, score=score, reward=reward))
    playground["album"] = album[-12:]
    return reward


ROOMS = {
    "playroom": {
        "title": "Игровая",
        "title_en": "Playroom",
        "icon": "🎮",
        "desc": "Играйте вдвоём, рисуйте и прыгайте по облакам.",
        "desc_en": "Play together, draw, and jump across the clouds.",
    },
    "kitchen": {
        "title": "Кухня",
        "title_en": "Kitchen",
        "icon": "🍽️",
        "desc": "Купите еду за монеты и накормите питомца.",
        "desc_en": "Buy food with coins and feed your companion.",
    },
    "bathroom": {
        "title": "Ванная",
        "title_en": "Bathroom",
        "icon": "🛁",
        "desc": "Искупайте питомца в ванне с тёплой пеной.",
        "desc_en": "Bathe your companion in a warm bubble bath.",
    },
    "bedroom": {
        "title": "Спальня",
        "title_en": "Bedroom",
        "icon": "🛏️",
        "desc": "Уложите питомца на кровать — во сне энергия восстановится.",
        "desc_en": "Tuck your companion into bed to restore energy while sleeping.",
    },
    "travel": {
        "title": "Путешествие",
        "title_en": "Travel",
        "icon": "✈️",
        "desc": "Соберите чемодан и выберите новое приключение для двоих.",
        "desc_en": "Pack a suitcase and choose a new adventure together.",
    },
}


FOODS = {
    "meal": {
        "title": "Корм",
        "title_en": "Meal",
        "icon": "🥣",
        "price": 5,
        "hunger": 0.18,
        "joy": 0.01,
    },
    "treat": {
        "title": "Лакомство",
        "title_en": "Treat",
        "icon": "🦴",
        "price": 8,
        "hunger": 0.12,
        "joy": 0.09,
    },
    "milk": {
        "title": "Молоко",
        "title_en": "Milk",
        "icon": "🥛",
        "price": 12,
        "hunger": 0.28,
        "joy": 0.04,
    },
}


def room_view(state, user_id, day=None):
    return {
        key: {
            "title": info["title"],
            "title_en": info["title_en"],
            "icon": info["icon"],
            "desc": info["desc"],
            "desc_en": info["desc_en"],
            "foods": (
                [{"key": food_key, **food} for food_key, food in FOODS.items()]
                if key == "kitchen"
                else []
            ),
        }
        for key, info in ROOMS.items()
    }


def buy_food(state, value):
    food = FOODS.get(value)
    if not food:
        raise ValueError("Еда не найдена")
    if state.get("sleeping"):
        raise ValueError("Сначала разбудите питомца")
    if float(state.get("hunger", 0)) >= 0.98:
        raise ValueError("Животик полон — покормите немного позже")
    coins = int(state.get("coins", 0))
    if coins < food["price"]:
        raise ValueError(f'Нужно ещё {food["price"] - coins} монет')
    state["coins"] = coins - food["price"]
    state["hunger"] = min(1.0, float(state.get("hunger", 0)) + food["hunger"])
    state["joy"] = min(1.0, float(state.get("joy", 0)) + food["joy"])
    return f'{food["title"]} куплено за {food["price"]} монет'
