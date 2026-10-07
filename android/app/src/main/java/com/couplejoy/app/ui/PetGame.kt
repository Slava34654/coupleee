package com.couplejoy.app.ui

import android.Manifest
import android.content.Context
import android.content.SharedPreferences
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.media.PlaybackParams
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.ApiClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import kotlin.math.max

// ---------- модель ----------
enum class CompanionType { UNCHOSEN, PET, BABY }

data class CompanionState(
    val type: CompanionType = CompanionType.UNCHOSEN,
    val name: String = "",
    val hunger: Float = 0.8f,
    val happiness: Float = 0.8f,
    val energy: Float = 0.8f,
    val clean: Float = 0.8f,
    val level: Int = 1,
    val xp: Float = 0f
)

val HATS = listOf("🧢" to 2, "🎀" to 4, "🎩" to 6, "👑" to 8)

// ---------- хранилище (обычные настройки, без новых библиотек) ----------
private object PetStore {
    fun load(p: SharedPreferences): CompanionState {
        val s = CompanionState(
            type = try {
                CompanionType.valueOf(p.getString("pet_type", "UNCHOSEN")!!)
            } catch (e: Exception) { CompanionType.UNCHOSEN },
            name = p.getString("pet_name", "") ?: "",
            hunger = p.getFloat("pet_hunger", 0.8f),
            happiness = p.getFloat("pet_happiness", 0.8f),
            energy = p.getFloat("pet_energy", 0.8f),
            clean = p.getFloat("pet_clean", 0.8f),
            level = p.getInt("pet_level", 1).coerceIn(1, 10),
            xp = p.getFloat("pet_xp", 0f)
        )
        if (s.type == CompanionType.UNCHOSEN) return s
        // Пока вас не было: проголодался, заскучал, испачкался (но выспался).
        val hours = max(0L, (System.currentTimeMillis() - p.getLong("pet_ts", 0L)) / 3600000L)
        if (hours <= 0) return s
        return s.copy(
            hunger = (s.hunger - 0.06f * hours).coerceIn(0f, 1f),
            happiness = (s.happiness - 0.05f * hours).coerceIn(0f, 1f),
            energy = (s.energy + 0.03f * hours).coerceIn(0f, 1f),
            clean = (s.clean - 0.04f * hours).coerceIn(0f, 1f)
        )
    }

    fun save(p: SharedPreferences, s: CompanionState) {
        p.edit()
            .putString("pet_type", s.type.name)
            .putString("pet_name", s.name)
            .putFloat("pet_hunger", s.hunger.coerceIn(0f, 1f))
            .putFloat("pet_happiness", s.happiness.coerceIn(0f, 1f))
            .putFloat("pet_energy", s.energy.coerceIn(0f, 1f))
            .putFloat("pet_clean", s.clean.coerceIn(0f, 1f))
            .putInt("pet_level", s.level.coerceIn(1, 10))
            .putFloat("pet_xp", s.xp.coerceIn(0f, 1f))
            .putLong("pet_ts", System.currentTimeMillis())
            .apply()
    }

    fun clear(p: SharedPreferences) {
        p.edit()
            .remove("pet_type").remove("pet_name").remove("pet_hunger")
            .remove("pet_happiness").remove("pet_energy").remove("pet_clean")
            .remove("pet_level").remove("pet_xp").remove("pet_ts")
            .apply()
    }
}

// ---------- экран ----------
@Composable
fun PetGameScreen(vm: AppVm, onBack: (() -> Unit)? = null) {
    val ctx = LocalContext.current
    val prefs = remember {
        ctx.getSharedPreferences("cj", Context.MODE_PRIVATE)
    }
    val scope = rememberCoroutineScope()
    var state by remember { mutableStateOf(PetStore.load(prefs)) }
    var confirmReset by remember { mutableStateOf(false) }
    var treats by remember { mutableStateOf(prefs.getInt("pet_treats", 3)) }
    var hat by remember { mutableStateOf(prefs.getString("pet_hat", "") ?: "") }
    var earnMsg by remember { mutableStateOf("") }
    val uid = vm.userId

    fun update(transform: (CompanionState) -> CompanionState) {
        var s = transform(state)
        if (s.xp >= 1f && s.level < 10) {
            s = s.copy(level = s.level + 1, xp = s.xp - 1f)
        } else if (s.level >= 10) {
            s = s.copy(xp = 1f)
        }
        PetStore.save(prefs, s)
        state = s
    }

    fun addTreats(n: Int) {
        treats += n
        prefs.edit().putInt("pet_treats", treats).apply()
    }

    // Вкусняшки за совместную активность пары (раз в сутки/викторину).
    LaunchedEffect(uid) {
        if (uid == null) return@LaunchedEffect
        try {
            var earned = 0
            val d = ApiClient.api.daily(uid)
            val dkey = "treat_daily_${d.question.date}"
            if (d.partner_answer != null && !prefs.getBoolean(dkey, false)) {
                earned += 2
                prefs.edit().putBoolean(dkey, true).apply()
            }
            for (q in ApiClient.api.quizzes()) {
                val r = ApiClient.api.quizResult(q.id, uid)
                val qkey = "treat_quiz_${q.id}"
                if (r.answered_together > 0 && !prefs.getBoolean(qkey, false)) {
                    earned += 1
                    prefs.edit().putBoolean(qkey, true).apply()
                }
            }
            if (earned > 0) {
                addTreats(earned)
                earnMsg = "Вкусняшки за вас двоих: +$earned 🎉"
            }
        } catch (e: Exception) {
            // без сети просто нет начислений
        }
    }

    ListScreen {
        item {
            Column {
                ScreenHeader("Питомец", "Вырастите малыша вместе — он ждёт заботы", onBack)
                Err(vm)
            }
        }
        if (earnMsg.isNotBlank()) {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 16.dp) {
                        Text(
                            earnMsg, color = Color.White,
                            style = MaterialTheme.typography.titleMedium,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }
        }
        if (state.type == CompanionType.UNCHOSEN) {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
                        PetChoice(
                            onStart = { type, name ->
                                val s = CompanionState(
                                    type = type, name = name,
                                    hunger = 0.8f, happiness = 0.8f,
                                    energy = 0.8f, clean = 0.8f,
                                    level = 1, xp = 0f
                                )
                                PetStore.save(prefs, s)
                                state = s
                            }
                        )
                    }
                }
            }
        } else {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
                        PetView(
                            state = state,
                            treats = treats,
                            hat = hat,
                            onHat = {
                                hat = it
                                prefs.edit().putString("pet_hat", it).apply()
                            },
                            onFeedRequest = {
                                if (treats <= 0) {
                                    false
                                } else {
                                    addTreats(-1)
                                    update {
                                        it.copy(
                                            hunger = it.hunger + 0.25f,
                                            energy = it.energy + 0.05f,
                                            xp = it.xp + 0.12f
                                        )
                                    }
                                    true
                                }
                            },
                            onPlay = {
                                update {
                                    it.copy(
                                        happiness = it.happiness + 0.25f,
                                        hunger = it.hunger - 0.1f,
                                        clean = it.clean - 0.05f,
                                        xp = it.xp + 0.15f
                                    )
                                }
                            },
                            onSleep = {
                                update {
                                    it.copy(
                                        energy = it.energy + 0.35f,
                                        happiness = it.happiness + 0.05f,
                                        xp = it.xp + 0.08f
                                    )
                                }
                            },
                            onBathe = {
                                update {
                                    it.copy(
                                        clean = 1f,
                                        happiness = it.happiness + 0.05f,
                                        xp = it.xp + 0.08f
                                    )
                                }
                            },
                            onPet = {
                                update {
                                    it.copy(
                                        happiness = it.happiness + 0.02f,
                                        xp = it.xp + 0.005f
                                    )
                                }
                            }
                        )
                    }
                }
            }
            item {
                Appear(1) {
                    GhostButton(
                        if (confirmReset) "Точно начать заново?" else "Начать заново",
                        {
                            if (confirmReset) {
                                PetStore.clear(prefs)
                                state = CompanionState()
                                confirmReset = false
                            } else {
                                confirmReset = true
                                scope.launch {
                                    delay(3000)
                                    confirmReset = false
                                }
                            }
                        },
                        Modifier.fillMaxWidth()
                    )
                }
            }
        }
    }
}

@Composable
private fun PetChoice(onStart: (CompanionType, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var mode by remember { mutableStateOf(0) } // 0 — питомец, 1 — малыш
    Column(
        Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            "Кого будем растить?", color = Color.White,
            style = MaterialTheme.typography.titleLarge
        )
        Spacer(Modifier.height(4.dp))
        Text(
            "10 уровней — от малыша до легенды",
            color = Color.White.copy(alpha = 0.85f),
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(14.dp))
        Segmented(listOf("🐱 Питомец", "👶 Малыш"), mode) { mode = it }
        Spacer(Modifier.height(14.dp))
        CjField(name, { name = it }, "Дайте имя")
        Spacer(Modifier.height(14.dp))
        PrimaryButton(
            "Начать путь роста",
            { onStart(if (mode == 0) CompanionType.PET else CompanionType.BABY, name.trim()) },
            Modifier.fillMaxWidth(), enabled = name.isNotBlank()
        )
    }
}

@Composable
private fun PetView(
    state: CompanionState,
    treats: Int,
    hat: String,
    onHat: (String) -> Unit,
    onFeedRequest: () -> Boolean,
    onPlay: () -> Unit,
    onSleep: () -> Unit,
    onBathe: () -> Unit,
    onPet: () -> Unit
) {
    val haptics = LocalHapticFeedback.current
    val scope = rememberCoroutineScope()
    var bounce by remember { mutableStateOf(false) }
    var hearts by remember { mutableStateOf(0) }
    var phrase by remember { mutableStateOf<String?>(null) }
    var playing by remember { mutableStateOf<String?>(null) }
    var petAcc by remember { mutableStateOf(0f) }
    var lastPetTick by remember { mutableStateOf(0L) }
    var dizzyUntil by remember { mutableStateOf(0L) }
    val tumbleAngle = remember { Animatable(0f) }
    var dragStart by remember { mutableStateOf(0L) }
    val s by animateFloatAsState(
        if (bounce) 1.18f else 1f, tween(220),
        finishedListener = { bounce = false }, label = "bounce"
    )
    // спокойное дыхание, когда никто не трогает
    val breathT = rememberInfiniteTransition(label = "breath")
    val breath by breathT.animateFloat(
        1f, 1.045f, infiniteRepeatable(tween(1600), RepeatMode.Reverse), label = "breath"
    )

    fun say(t: String) {
        phrase = t
        scope.launch {
            delay(1600)
            if (phrase == t) phrase = null
        }
    }
    fun love(n: Int) {
        hearts += n
        scope.launch {
            delay(900)
            hearts = max(0, hearts - n)
        }
    }
    fun poke() {
        bounce = true
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        love(2)
        val line = if (state.type == CompanionType.PET) {
            listOf("Мурр!", "Мяу!", "Хи-хи!", "Ещё-ещё!").random()
        } else {
            listOf("Агу!", "Хи-хи!", "Бу!", "Ещё!").random()
        }
        say(line)
    }
    fun tumble() {
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        dizzyUntil = System.currentTimeMillis() + 1800
        say("Уиии! 🤪")
        scope.launch {
            tumbleAngle.animateTo(360f, tween(650))
            tumbleAngle.snapTo(0f)
        }
    }
    fun doEat() {
        if (!onFeedRequest()) {
            say("Нет вкусняшек 🍪 Ответьте вместе на вопрос дня!")
            return
        }
        playing = "eat"
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        say(if (state.type == CompanionType.PET) "Ням-ням!" else "Ам-ам!")
        scope.launch {
            delay(1500)
            if (playing == "eat") playing = null
        }
    }
    fun doPlay() {
        bounce = true
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        love(3)
        say(if (state.type == CompanionType.PET) "Ура, играем!" else "Юхуу!")
        onPlay()
    }
    fun doSleep() {
        playing = "sleep"
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        say("Сплю... Zzz")
        onSleep()
        scope.launch {
            delay(2500)
            if (playing == "sleep") playing = null
        }
    }
    fun doBathe() {
        bounce = true
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        love(2)
        say("Чисто-чисто! 🫧")
        onBathe()
    }

    val (stageEmoji, stage) = growthStage(state)
    val dizzy = System.currentTimeMillis() < dizzyUntil
    val face = when {
        dizzy -> "😵"
        playing == "eat" -> "😋"
        playing == "sleep" -> "😴"
        else -> stageEmoji
    }
    val food = foodForLevel(state.level, state.type)
    val toy = toyForLevel(state.level, state.type)

    Column(
        Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    state.name, color = Color.White, fontSize = 22.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    stage, color = Color.White.copy(alpha = 0.85f),
                    style = MaterialTheme.typography.labelMedium
                )
            }
            Text(
                "Ур. ${state.level}/10",
                Modifier.clip(RoundedCornerShape(50))
                    .background(Color.White.copy(alpha = 0.22f))
                    .padding(horizontal = 14.dp, vertical = 6.dp),
                color = Color.White, style = MaterialTheme.typography.labelLarge
            )
        }
        Spacer(Modifier.height(6.dp))
        // сердечки и фразы
        Box(Modifier.fillMaxWidth().height(34.dp), Alignment.Center) {
            if (hearts > 0) {
                Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                    repeat(hearts.coerceAtMost(8)) { i ->
                        Text("💖", fontSize = (16 + (i % 3) * 4).sp)
                    }
                }
            } else if (phrase != null) {
                Text(
                    phrase!!, color = Color.White,
                    style = MaterialTheme.typography.titleMedium
                )
            }
        }
        // САМ ПИТОМЕЦ: тап — тыкнуть, гладить — вести пальцем, швырнуть — резкий свайп
        Box(
            Modifier.size(140.dp)
                .graphicsLayer {
                    scaleX = s * breath
                    scaleY = s * breath
                    rotationZ = tumbleAngle.value
                }
                .clip(CircleShape)
                .background(
                    Brush.radialGradient(
                        listOf(Color.White.copy(alpha = 0.35f), Color.Transparent)
                    )
                )
                .pointerInput(Unit) {
                    detectTapGestures(onTap = { poke() })
                }
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = {
                            petAcc = 0f
                            dragStart = System.currentTimeMillis()
                        },
                        onDrag = { change, _ ->
                            change.consume()
                            petAcc += (change.position - change.previousPosition).getDistance()
                            val now = System.currentTimeMillis()
                            if (petAcc >= 12f && now - lastPetTick > 400) {
                                petAcc = 0f
                                lastPetTick = now
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                love(1)
                                onPet()
                            }
                        },
                        onDragEnd = {
                            val dt = System.currentTimeMillis() - dragStart
                            if (petAcc >= 500f && dt < 900) tumble()
                            petAcc = 0f
                        },
                        onDragCancel = { petAcc = 0f }
                    )
                },
            contentAlignment = Alignment.Center
        ) {
            Text(face, fontSize = 64.sp)
            if (hat.isNotBlank()) {
                Text(
                    hat, fontSize = 38.sp,
                    modifier = Modifier.align(Alignment.TopCenter).offset(y = (-14).dp)
                )
            }
        }
        Text(
            "тыкни, погладь или швырни 👆",
            color = Color.White.copy(alpha = 0.6f),
            style = MaterialTheme.typography.labelMedium
        )
        Spacer(Modifier.height(14.dp))
        PetBar("Прогресс уровня", state.xp, state.level == 10)
        Spacer(Modifier.height(10.dp))
        PetBar("Сытость", state.hunger, false)
        Spacer(Modifier.height(6.dp))
        PetBar("Радость", state.happiness, false)
        Spacer(Modifier.height(6.dp))
        PetBar("Энергия", state.energy, false)
        Spacer(Modifier.height(6.dp))
        PetBar("Чистота", state.clean, false)
        Spacer(Modifier.height(16.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            PetAction(food, "Кормить\n×$treats") { doEat() }
            PetAction(toy, "Играть") { doPlay() }
            PetAction("🌙", "Спать") { doSleep() }
            PetAction("🧼", "Мыть") { doBathe() }
        }
        Spacer(Modifier.height(14.dp))
        VoiceButton()
        Spacer(Modifier.height(14.dp))
        Text(
            "Гардероб",
            color = Color.White.copy(alpha = 0.85f),
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(Modifier.height(8.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            WardrobeHat("🚫", "Без шапки", state.level >= 1, hat.isBlank()) { onHat("") }
            HATS.forEach { (emoji, need) ->
                WardrobeHat(
                    emoji, "Ур. $need",
                    state.level >= need, hat == emoji
                ) { if (state.level >= need) onHat(emoji) }
            }
        }
    }
}

@Composable
private fun WardrobeHat(emoji: String, sub: String, unlocked: Boolean, selected: Boolean, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.clickable(onClick = onClick)) {
        Box(
            Modifier.size(56.dp).clip(CircleShape)
                .background(
                    if (selected) Color.White.copy(alpha = 0.35f)
                    else Color.White.copy(alpha = 0.12f)
                )
                .border(
                    1.5.dp,
                    if (selected) Color.White else Color.White.copy(alpha = 0.3f),
                    CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(if (unlocked) emoji else "🔒", fontSize = 26.sp)
        }
        Spacer(Modifier.height(2.dp))
        Text(
            sub, style = MaterialTheme.typography.labelMedium,
            color = Color.White.copy(alpha = if (unlocked) 0.9f else 0.5f)
        )
    }
}

// ---------- голос питомца: записать и смешно повторить ----------
@Composable
private fun VoiceButton() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var mode by remember { mutableStateOf(0) } // 0 ждёт, 1 пишет, 2 есть запись
    var secs by remember { mutableStateOf(0) }
    var msg by remember { mutableStateOf("") }
    var rec by remember { mutableStateOf<MediaRecorder?>(null) }
    var path by remember { mutableStateOf<String?>(null) }

    fun stopAndPlay() {
        val p = path
        try { rec?.stop() } catch (e: Exception) { }
        try { rec?.release() } catch (e: Exception) { }
        rec = null
        if (p == null || secs < 1) {
            mode = 0
            return
        }
        mode = 2
        try {
            val mp = MediaPlayer()
            mp.setDataSource(p)
            mp.prepare()
            if (Build.VERSION.SDK_INT >= 23) {
                mp.playbackParams = PlaybackParams().setPitch(1.8f)
            }
            mp.setOnCompletionListener { it.release() }
            mp.start()
        } catch (e: Exception) {
            msg = "Не вышло 🎤"
        }
    }

    fun startRec() {
        msg = ""
        try {
            val f = File(ctx.cacheDir, "pet_voice.3gp")
            val r = if (Build.VERSION.SDK_INT >= 31) MediaRecorder(ctx) else MediaRecorder()
            r.setAudioSource(MediaRecorder.AudioSource.MIC)
            r.setOutputFormat(MediaRecorder.OutputFormat.THREE_GPP)
            r.setAudioEncoder(MediaRecorder.AudioEncoder.AMR_NB)
            r.setOutputFile(f.absolutePath)
            r.prepare()
            r.start()
            rec = r
            path = f.absolutePath
            secs = 0
            mode = 1
        } catch (e: Exception) {
            msg = "Нет доступа к микрофону 🎤"
        }
    }

    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        if (ok) startRec() else msg = "Разреши микрофон в настройках 🎤"
    }

    if (mode == 1) {
        LaunchedEffect(Unit) {
            while (true) {
                delay(1000)
                secs++
                if (secs >= 10) stopAndPlay()
            }
        }
    }

    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        PetAction(
            if (mode == 1) "⏹️" else "🎤",
            when {
                mode == 1 -> "$secs с · стоп"
                msg.isNotBlank() -> msg
                else -> "Голос"
            }
        ) {
            if (mode == 1) stopAndPlay()
            else perm.launch(Manifest.permission.RECORD_AUDIO)
        }
    }
    if (mode == 1) {
        Spacer(Modifier.height(6.dp))
        Text(
            "● идёт запись… скажи что-нибудь!",
            color = Color.White, style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun PetBar(label: String, value: Float, maxed: Boolean) {
    Column(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                label, style = MaterialTheme.typography.labelMedium,
                color = Color.White.copy(alpha = 0.85f)
            )
            Text(
                if (maxed) "MAX" else "${(value * 100).toInt().coerceIn(0, 100)}%",
                style = MaterialTheme.typography.labelMedium,
                color = Color.White.copy(alpha = 0.85f)
            )
        }
        Spacer(Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { value.coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(50)),
            color = Color.White,
            trackColor = Color.White.copy(alpha = 0.25f)
        )
    }
}

@Composable
private fun PetAction(emoji: String, label: String, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            Modifier.size(64.dp).clip(CircleShape)
                .background(Color.White.copy(alpha = 0.22f))
                .border(1.5.dp, Color.White.copy(alpha = 0.5f), CircleShape)
                .clickable(onClick = onClick),
            contentAlignment = Alignment.Center
        ) {
            Text(emoji, fontSize = 30.sp)
        }
        Spacer(Modifier.height(4.dp))
        Text(
            label, style = MaterialTheme.typography.labelMedium,
            color = Color.White.copy(alpha = 0.9f),
            textAlign = TextAlign.Center
        )
    }
}

// ---------- стадии роста ----------
private fun growthStage(s: CompanionState): Pair<String, String> {
    if (s.hunger < 0.25f) return (if (s.type == CompanionType.PET) "😿" else "😭") to "Очень голоден! Покорми"
    if (s.energy < 0.25f) return "😴" to "Устал, уложи спать"
    if (s.happiness < 0.25f) return "🥺" to "Скучает, поиграй"
    if (s.clean < 0.25f) return "🛁" to "Грязнуля! Помой меня"
    return when (s.type) {
        CompanionType.PET -> when (s.level) {
            1 -> "🐱" to "1 · Новорожденный котёнок"
            2 -> "🐾" to "2 · Пушистый малыш"
            3 -> "🐈" to "3 · Игривый котик"
            4 -> "🐈‍⬛" to "4 · Ловкий охотник"
            5 -> "🦊" to "5 · Хитрый лисёнок"
            6 -> "🐆" to "6 · Быстрый гепард"
            7 -> "🐅" to "7 · Сильный тигр"
            8 -> "🦁" to "8 · Царь зверей"
            9 -> "🐉" to "9 · Мифический дракон"
            else -> "👑" to "10 · Легендарный правитель"
        }
        CompanionType.BABY -> when (s.level) {
            1 -> "👶" to "1 · Младенец"
            2 -> "🍼" to "2 · Ползающий малыш"
            3 -> "🧒" to "3 · Дошкольник"
            4 -> "👦" to "4 · Школьник"
            5 -> "🧑" to "5 · Подросток"
            6 -> "👨‍🎓" to "6 · Студент"
            7 -> "👨‍💼" to "7 · Молодой специалист"
            8 -> "🧔" to "8 · Мудрый мастер"
            9 -> "🦸" to "9 · Герой"
            else -> "👑" to "10 · Абсолютная легенда"
        }
        CompanionType.UNCHOSEN -> "❓" to "Не выбран"
    }
}

private fun foodForLevel(level: Int, type: CompanionType): String {
    if (type == CompanionType.BABY) return when (level) {
        1, 2 -> "🍼"
        3, 4 -> "🥣"
        else -> "🍕"
    }
    return when (level) {
        1, 2 -> "🍼"
        3, 4 -> "🥣"
        5, 6 -> "🍔"
        7, 8 -> "🍕"
        else -> "🍱"
    }
}

private fun toyForLevel(level: Int, type: CompanionType): String {
    if (type == CompanionType.BABY) return when (level) {
        1, 2 -> "🪇"
        3, 4 -> "🧸"
        else -> "🎮"
    }
    return when (level) {
        1, 2 -> "🪇"
        3, 4 -> "🧸"
        5, 6 -> "⚽"
        7, 8 -> "🎮"
        else -> "🤖"
    }
}
