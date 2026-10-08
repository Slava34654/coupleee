package com.couplejoy.app.ui

import java.time.Instant
import java.time.ZoneId

/** Pure game rules, independent of rendering, storage, and Android. */
data class CareState(
    val type: String = "PET", val name: String = "", val adopted: Boolean = false,
    val hunger: Float = .72f, val joy: Float = .72f, val energy: Float = .8f,
    val clean: Float = .8f, val bond: Int = 0, val level: Int = 1, val xp: Int = 0,
    val coins: Int = 20, val sleeping: Boolean = false,
    val timestamp: Long = 0L, val lastAction: Long = 0L,
    val cooldowns: Map<String, Long> = emptyMap(),
    val day: String = "", val dailyActions: Set<String> = emptySet(),
    val rewardedDay: String = "", val careDay: String = "", val streak: Int = 0,
    val room: String = "rose", val ownedRooms: Set<String> = setOf("rose"),
    val accessory: String = "none"
)

data class CareResult(val state: CareState, val message: String, val animation: String = "idle")

object CareEngine {
    val rooms = linkedMapOf("rose" to 0, "garden" to 40, "night" to 65, "beach" to 90)
    fun day(now: Long): String = Instant.ofEpochMilli(now).atZone(ZoneId.systemDefault()).toLocalDate().toString()
    fun requiredXp(level: Int) = 60 + level * 20

    fun advance(s: CareState, now: Long): CareState {
        val hours = if (s.timestamp == 0L) 0f else ((now - s.timestamp).coerceIn(0, 24 * 3600000L) / 3600000f)
        val today = day(now)
        return s.copy(
            hunger = (s.hunger - hours * if (s.sleeping) .018f else .035f).coerceIn(.12f, 1f),
            joy = (s.joy - hours * .022f).coerceIn(.15f, 1f),
            clean = (s.clean - hours * .025f).coerceIn(.15f, 1f),
            energy = (s.energy + hours * if (s.sleeping) .4f else -.035f).coerceIn(.12f, 1f),
            timestamp = maxOf(s.timestamp, now), day = today,
            dailyActions = if (today == s.day) s.dailyActions else emptySet()
        )
    }

    fun act(original: CareState, action: String, now: Long): CareResult {
        val s = advance(original, now)
        if (!s.adopted) return CareResult(s, "Сначала выберите малыша и имя")
        if (now - s.lastAction < 2500L) return CareResult(s, "Подождите, малыш ещё занят")
        if (action == "sleep") {
            if (!s.sleeping && s.energy >= .95f) return CareResult(s, "Я уже выспался! Давайте поиграем")
            return CareResult(s.copy(sleeping = !s.sleeping, lastAction = now),
                if (s.sleeping) "Доброе утро!" else "Тихий час · энергия растёт даже после закрытия приложения",
                if (s.sleeping) "love" else "sleep")
        }
        if (s.sleeping) return CareResult(s, "Сначала разбудите малыша — пусть откроет глазки")
        val remaining = ((s.cooldowns[action] ?: 0L) - now + 45000L)
        if (remaining > 0) return CareResult(s, "Ещё ${(remaining + 999) / 1000} с — можно попробовать другое действие")
        var next = when (action) {
            "feed" -> {
                if (s.hunger >= .92f) return CareResult(s, "Животик полон — покормите немного позже")
                s.copy(hunger = (s.hunger + .25f).coerceAtMost(1f), joy = (s.joy + .03f).coerceAtMost(1f))
            }
            "play" -> {
                if (s.energy < .25f) return CareResult(s, "Сначала поспим: для игры нужна энергия")
                if (s.hunger < .2f) return CareResult(s, "Сначала перекусим, а потом поиграем")
                if (s.joy >= .95f) return CareResult(s, "Я счастлив! Давай немного отдохнём")
                s.copy(joy = (s.joy + .24f).coerceAtMost(1f), energy = (s.energy - .12f).coerceAtLeast(.12f),
                    hunger = (s.hunger - .07f).coerceAtLeast(.12f), clean = (s.clean - .06f).coerceAtLeast(.15f))
            }
            "wash" -> {
                if (s.clean >= .95f) return CareResult(s, "Уже чистенький! Можно обнять")
                s.copy(clean = 1f, joy = (s.joy + .04f).coerceAtMost(1f))
            }
            "love" -> s.copy(joy = (s.joy + .06f).coerceAtMost(1f), bond = (s.bond + 1).coerceAtMost(100))
            else -> return CareResult(s, "Неизвестное действие")
        }
        val today = day(now)
        val yesterday = Instant.ofEpochMilli(now).atZone(ZoneId.systemDefault()).toLocalDate().minusDays(1).toString()
        val actions = s.dailyActions + action
        val dailyReward = actions.size >= 3 && s.rewardedDay != today
        next = next.copy(
            xp = s.xp + (if (action == "love") 3 else 10),
            coins = s.coins + (if (action == "love") 0 else 2) + (if (dailyReward) 15 else 0),
            dailyActions = actions, rewardedDay = if (dailyReward) today else s.rewardedDay,
            careDay = today, streak = if (s.careDay == today) s.streak else if (s.careDay == yesterday) s.streak + 1 else 1,
            cooldowns = s.cooldowns + (action to now), lastAction = now
        )
        while (next.level < 10 && next.xp >= requiredXp(next.level)) {
            next = next.copy(xp = next.xp - requiredXp(next.level), level = next.level + 1, coins = next.coins + 20)
        }
        if (next.level == 10) next = next.copy(xp = minOf(next.xp, requiredXp(10)))
        val message = when {
            next.level > s.level -> "Новый уровень ${next.level}! +20 монет · малыш подрос"
            dailyReward -> "Забота дня выполнена! +15 монет"
            action == "feed" -> "Ням! Спасибо за вкусный обед"
            action == "wash" -> "Пузырьки! Теперь я чистенький"
            action == "play" -> "Ура! Обожаю играть с тобой"
            else -> "Как хорошо рядом с тобой ♥"
        }
        return CareResult(next, message, action)
    }

    fun room(s: CareState, id: String): CareResult {
        val price = rooms[id] ?: return CareResult(s, "Комната не найдена")
        if (id in s.ownedRooms) return CareResult(s.copy(room = id), "Комната выбрана")
        if (s.coins < price) return CareResult(s, "Нужно ещё ${price - s.coins} монет")
        return CareResult(s.copy(room = id, coins = s.coins - price, ownedRooms = s.ownedRooms + id), "Комната ваша навсегда ✨")
    }
}
