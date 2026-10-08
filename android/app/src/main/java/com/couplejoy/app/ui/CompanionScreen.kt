package com.couplejoy.app.ui

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.couplejoy.app.AppVm
import com.google.gson.Gson
import kotlinx.coroutines.delay

@Composable
fun PetGameScreen(vm: AppVm, onBack: (() -> Unit)? = null, onGames: () -> Unit = {}) {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("cj", Context.MODE_PRIVATE) }
    val key = "companion_3d_${vm.userId ?: "local"}"
    val gson = remember { Gson() }
    var state by remember(key) {
        val saved = runCatching { prefs.getString(key, null)?.let { gson.fromJson(it, CareState::class.java) } }.getOrNull()
        val legacy = CareState(
            type = if (prefs.getString("pet_type", "") == "BABY") "BABY" else "PET",
            name = prefs.getString("pet_name", "") ?: "",
            adopted = prefs.getString("pet_type", "UNCHOSEN") in listOf("PET", "BABY"),
            hunger = prefs.getFloat("pet_hunger", .72f).coerceIn(.12f, 1f),
            joy = prefs.getFloat("pet_happiness", .72f).coerceIn(.15f, 1f),
            energy = prefs.getFloat("pet_energy", .8f).coerceIn(.12f, 1f),
            clean = prefs.getFloat("pet_clean", .8f).coerceIn(.15f, 1f),
            level = prefs.getInt("pet_level", 1).coerceIn(1, 10),
            xp = (prefs.getFloat("pet_xp", 0f).coerceIn(0f, 1f) * CareEngine.requiredXp(prefs.getInt("pet_level", 1).coerceIn(1, 10))).toInt(),
            coins = prefs.getInt("pet_coins", 20).coerceAtLeast(0),
            bond = prefs.getInt("pet_bond", 0).coerceIn(0, 100),
            timestamp = prefs.getLong("pet_ts", System.currentTimeMillis())
        )
        mutableStateOf(CareEngine.advance(saved ?: legacy, System.currentTimeMillis()))
    }
    var name by remember { mutableStateOf(state.name) }
    var message by remember { mutableStateOf("Маленький мир, в котором вас всегда ждут") }
    var animation by remember { mutableStateOf("idle") }
    var eventId by remember { mutableStateOf(0) }
    var sceneReady by remember { mutableStateOf(false) }
    var sceneFailed by remember { mutableStateOf(false) }
    var reset by remember { mutableStateOf(false) }
    var rename by remember { mutableStateOf(false) }
    var help by remember { mutableStateOf(false) }
    fun save(next: CareState) {
        state = next
        prefs.edit().putString(key, gson.toJson(next)).apply()
    }
    fun act(action: String) {
        val result = CareEngine.act(state, action, System.currentTimeMillis())
        save(result.state); message = result.message
        if (result.animation != "idle") { animation = result.animation; eventId++ }
    }
    LaunchedEffect(key) {
        save(state)
        while (true) {
            delay(15000)
            if (state.adopted) save(CareEngine.advance(state, System.currentTimeMillis()))
        }
    }
    val x = LocalCj.current
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(if (state.adopted) state.name + " ✎" else "Новый друг", style = MaterialTheme.typography.headlineMedium,
                    modifier = Modifier.clickable(enabled = state.adopted) { name = state.name; rename = true })
                Text(if (state.type == "BABY") "Ваш маленький малыш · 3D" else "Ваш ласковый котёнок · 3D",
                    style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            TextButton(onClick = { help = true }) { Text("Как играть") }
        }
        if (!state.adopted) Segmented(listOf("Котёнок", "Малыш"), if (state.type == "PET") 0 else 1) {
            save(state.copy(type = if (it == 0) "PET" else "BABY"))
        }
        Box(Modifier.fillMaxWidth().height(350.dp).clip(RoundedCornerShape(28.dp))) {
            CompanionScene(state, animation, eventId, Modifier.fillMaxSize(),
                onPet = { if (state.adopted) act("love") else { animation = "love"; eventId++ } },
                onReady = { sceneReady = true }, onError = { sceneFailed = true })
            if (!sceneReady && !sceneFailed) CircularProgressIndicator(Modifier.align(Alignment.Center).size(32.dp), color = x.accentA)
            if (sceneFailed) Text("3D недоступно на этом устройстве. Уход и прогресс продолжают работать.",
                Modifier.align(Alignment.Center).background(x.card).padding(18.dp), color = x.accentA)
            if (state.adopted) {
                Row(Modifier.align(Alignment.TopCenter).fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Pill("Уровень ${state.level}", Color(0xFF865674))
                    Pill("${state.coins} монет", Color(0xFF96682F))
                }
            }
        }
        if (!state.adopted) {
            SoftCard(Modifier.fillMaxWidth()) {
                Text("Большая дружба начинается с имени", style = MaterialTheme.typography.titleLarge)
                Spacer(Modifier.height(8.dp))
                Text("Кормите, играйте и обнимайте. Малыш будет расти, а ваша комната — становиться уютнее.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(14.dp))
                CjField(name, { name = it.take(24) }, "Как его зовут?")
                Spacer(Modifier.height(14.dp))
                PrimaryButton("Поселить у нас ♥", {
                    save(state.copy(name = name.trim(), adopted = true, timestamp = System.currentTimeMillis()))
                    message = "Привет, я ${name.trim()}! Давай познакомимся"; animation = "love"; eventId++
                }, Modifier.fillMaxWidth(), enabled = name.isNotBlank())
            }
        } else {
            Text(message, Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(x.accentA.copy(.09f)).padding(14.dp),
                color = x.accentA, style = MaterialTheme.typography.bodyMedium)
            SoftCard(Modifier.fillMaxWidth(), padding = 16.dp) {
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    CareMeter("Сытость", state.hunger, Color(0xFFCC9870), Modifier.weight(1f))
                    CareMeter("Радость", state.joy, x.accentA, Modifier.weight(1f))
                }
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    CareMeter(if (state.sleeping) "Сон · +40%/ч" else "Энергия", state.energy, Color(0xFF8D8AC0), Modifier.weight(1f))
                    CareMeter("Чистота", state.clean, Color(0xFF71AAA5), Modifier.weight(1f))
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PrimaryButton(if (state.type == "BABY") "🍼 Кормить" else "🥣 Кормить", { act("feed") }, Modifier.weight(1f), enabled = !state.sleeping)
                PrimaryButton("🎮 Играть", onGames, Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                GhostButton(if (state.sleeping) "☀ Разбудить" else "☾ Уложить", { act("sleep") }, Modifier.weight(1f))
                PrimaryButton("🫧 Купать", { act("wash") }, Modifier.weight(1f), enabled = !state.sleeping)
            }
            GhostButton("♥ Обнять", { act("love") }, Modifier.fillMaxWidth())
            SoftCard(Modifier.fillMaxWidth()) {
                Text("Растём с любовью", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                ProgressBar(state.xp.toFloat() / CareEngine.requiredXp(state.level))
                Spacer(Modifier.height(6.dp))
                Text(if (state.level >= 10) "Максимальный уровень · самый любимый" else "${state.xp} / ${CareEngine.requiredXp(state.level)} опыта · следующий уровень: +20 монет",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(10.dp))
                Text("♥ Связь ${state.bond}%   ·   Забота ${state.streak} дн.", color = x.accentA, fontSize = 13.sp)
            }
            SoftCard(Modifier.fillMaxWidth()) {
                val complete = state.rewardedDay == CareEngine.day(System.currentTimeMillis())
                Text(if (complete) "Забота дня выполнена ✓" else "Три маленьких проявления заботы", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(6.dp))
                Text(if (complete) "+15 монет уже в копилке" else "${state.dailyActions.size.coerceAtMost(3)} / 3 разных действия · награда 15 монет",
                    color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 13.sp)
                Spacer(Modifier.height(10.dp))
                ProgressBar(if (complete) 1f else state.dailyActions.size / 3f)
            }
            Text("Уютная комната", style = MaterialTheme.typography.titleLarge)
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                val names = mapOf("rose" to "🌸 Розовая", "garden" to "🌿 Сад", "night" to "🌙 Вечер", "beach" to "🏖 Пляж")
                CareEngine.rooms.forEach { (id, cost) ->
                    SoftCard(Modifier.width(136.dp), onClick = {
                        val result = CareEngine.room(state, id); save(result.state); message = result.message
                    }, padding = 14.dp) {
                        Text(names.getValue(id), fontWeight = FontWeight.SemiBold)
                        Text(if (id == state.room) "Выбрана ✓" else if (id in state.ownedRooms) "Выбрать" else "$cost монет",
                            color = x.accentA, fontSize = 12.sp)
                    }
                }
            }
            SoftCard(Modifier.fillMaxWidth()) {
                Text("Маленькие украшения", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(Triple("none", "Без украшения", 1), Triple("bow", "Бантик · ур. 2", 2), Triple("crown", "Корона · ур. 5", 5)).forEach { (id, label, level) ->
                        FilterChip(selected = state.accessory == id, enabled = state.level >= level,
                            onClick = { save(state.copy(accessory = id)) }, label = { Text(label) })
                    }
                }
            }
            Text("Прогресс хранится на этом устройстве. 3D и уход работают без интернета.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            TextButton(onClick = { reset = true }) { Text("Выбрать нового друга", color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
    }
    if (rename) AlertDialog(onDismissRequest = { rename = false }, title = { Text("Имя малыша") },
        text = { CjField(name, { name = it.take(24) }, "Имя") },
        confirmButton = { TextButton(enabled = name.isNotBlank(), onClick = { save(state.copy(name = name.trim())); rename = false }) { Text("Сохранить") } },
        dismissButton = { TextButton(onClick = { rename = false }) { Text("Отмена") } })
    if (help) AlertDialog(onDismissRequest = { help = false }, title = { Text("Забота без спешки") },
        text = { Text("Поверните малыша пальцем, коснитесь его для объятий.\n\nКормление повышает сытость. Игра радует, но расходует энергию. Купание возвращает чистоту. Сон восстанавливает 40% энергии в час, даже когда приложение закрыто.\n\nОдинаковое действие — раз в 45 секунд. Три разных действия в день дают 15 монет. Комнаты покупаются один раз. За уровень — ещё 20 монет.\n\nМалыш не погибает и не теряет уровни, пока вас нет.") },
        confirmButton = { TextButton(onClick = { help = false }) { Text("Понятно") } })
    if (reset) AlertDialog(onDismissRequest = { reset = false }, title = { Text("Поселить нового друга?") },
        text = { Text("Имя, уровень, монеты и комнаты текущего малыша будут сброшены. Записи дневника сохранятся.") },
        confirmButton = { TextButton(onClick = {
            save(CareState(timestamp = System.currentTimeMillis())); name = ""; reset = false
            message = "Знакомимся заново"; animation = "idle"; eventId++
        }) { Text("Начать заново") } }, dismissButton = { TextButton(onClick = { reset = false }) { Text("Оставить малыша") } })
}

@Composable
private fun CareMeter(label: String, value: Float, tint: Color, modifier: Modifier) {
    Column(modifier) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("${(value * 100).toInt()}%", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
        Spacer(Modifier.height(6.dp))
        LinearProgressIndicator(progress = { value }, modifier = Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(8.dp)),
            color = tint, trackColor = tint.copy(.12f))
    }
}
