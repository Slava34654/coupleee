package com.couplejoy.app.ui

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animate
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Logout
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Casino
import androidx.compose.material.icons.rounded.ChevronRight
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.DarkMode
import androidx.compose.material.icons.rounded.Favorite
import androidx.compose.material.icons.rounded.HourglassTop
import androidx.compose.material.icons.rounded.LightMode
import androidx.compose.material.icons.rounded.PhotoCamera
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Quiz
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Style
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.AnswerReq
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.DailyResp
import com.couplejoy.app.api.EventReq
import com.couplejoy.app.api.EventResp
import com.couplejoy.app.api.Idea
import com.couplejoy.app.api.IdeaReq
import com.couplejoy.app.api.JoinReq
import com.couplejoy.app.api.JournalEntry
import com.couplejoy.app.api.JournalReq
import com.couplejoy.app.api.MeResp
import com.couplejoy.app.api.MoodReq
import com.couplejoy.app.api.PackAnsReq
import com.couplejoy.app.api.PackResp
import com.couplejoy.app.api.PackShort
import com.couplejoy.app.api.PairReq
import com.couplejoy.app.api.QuizAnsReq
import com.couplejoy.app.api.QuizResp
import com.couplejoy.app.api.QuizResult
import com.couplejoy.app.api.QuizShort
import com.couplejoy.app.api.WidgetPhoto
import com.couplejoy.app.api.WidgetReq
import kotlinx.coroutines.launch

// ---------- общий каркас списка ----------
@Composable
private fun ListScreen(content: LazyListScope.() -> Unit) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 12.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = content
    )
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text, style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}

@Composable
private fun ActionTile(
    modifier: Modifier, icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String, sub: String, onClick: () -> Unit
) {
    SoftCard(modifier, onClick = onClick) {
        IconBadge(icon)
        Spacer(Modifier.height(12.dp))
        Text(title, style = MaterialTheme.typography.titleMedium)
        Text(sub, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

// ---------- вход / создание пары ----------
@Composable
fun PairScreen(vm: AppVm, onDone: (Int, LocalProfile) -> Unit) {
    val x = LocalCj.current
    val ctx = LocalContext.current
    var name by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var myCode by remember { mutableStateOf<String?>(null) }
    var myUid by remember { mutableStateOf<Int?>(null) }
    var birth by remember { mutableStateOf("") }
    var since by remember { mutableStateOf("") }
    var avatarUri by remember { mutableStateOf<Uri?>(null) }
    var avatarUrl by remember { mutableStateOf("") }
    var mode by remember { mutableStateOf(0) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {
        if (it != null) avatarUri = it
    }

    val pulse = rememberInfiniteTransition(label = "logo")
    val ps by pulse.animateFloat(
        1f, 1.08f, infiniteRepeatable(tween(1100), RepeatMode.Reverse), label = "logos"
    )

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Spacer(Modifier.height(12.dp))
        Box(
            Modifier.size(96.dp).graphicsLayer { scaleX = ps; scaleY = ps }
                .clip(RoundedCornerShape(30.dp)).background(x.brand()),
            Alignment.Center
        ) {
            Icon(Icons.Rounded.Favorite, null, tint = Color.White, modifier = Modifier.size(52.dp))
        }
        Text(
            "CoupleJoy",
            style = MaterialTheme.typography.displaySmall.copy(brush = x.brand())
        )
        Text(
            "Пространство для двоих: настроение, вопросы, свидания и общий журнал.",
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(4.dp))
        SoftCard(Modifier.fillMaxWidth()) {
            Segmented(listOf("Создать пару", "Присоединиться"), mode) { mode = it }
            Spacer(Modifier.height(16.dp))

            // фото профиля
            Box(
                Modifier.align(Alignment.CenterHorizontally).size(104.dp).clip(CircleShape)
                    .background(x.accentA.copy(alpha = 0.10f), CircleShape)
                    .border(2.dp, x.accentA.copy(alpha = 0.5f), CircleShape)
                    .clickable { pick.launch("image/*") },
                Alignment.Center
            ) {
                val u = avatarUri
                if (u == null) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Rounded.PhotoCamera, null, tint = x.accentA, modifier = Modifier.size(30.dp))
                        Text("Фото", color = x.accentA, style = MaterialTheme.typography.labelMedium)
                    }
                } else {
                    AsyncImage(u, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                }
            }
            Spacer(Modifier.height(14.dp))
            CjField(name, { name = it }, "Ваше имя")
            Spacer(Modifier.height(12.dp))
            DateField("Дата рождения (необязательно)", birth, { birth = it })
            Spacer(Modifier.height(12.dp))
            DateField("Вместе с…", since, { since = it })
            Spacer(Modifier.height(6.dp))
            Text(
                "Счётчик «дней вместе» будет сам расти каждый день.",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(14.dp))

            if (mode == 0) {
                PrimaryButton(
                    if (busy) "Создаём…" else "Создать пару",
                    {
                        scope.launch {
                            busy = true
                            try {
                                val av = avatarUri?.let { uploadImage(ctx, it) } ?: ""
                                val r = ApiClient.api.pair(PairReq(name, birth, av))
                                avatarUrl = av
                                myCode = r.pair_code
                                myUid = r.user_id
                            } catch (e: Exception) { vm.error = e.message }
                            busy = false
                        }
                    },
                    Modifier.fillMaxWidth(),
                    enabled = name.isNotBlank() && since.isNotBlank() && !busy && myUid == null
                )
                myCode?.let { c ->
                    Spacer(Modifier.height(16.dp))
                    Column(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp))
                            .background(x.accentA.copy(alpha = 0.10f))
                            .border(1.dp, x.accentA.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
                            .padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("Код вашей пары", style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            c, fontSize = 34.sp, fontWeight = FontWeight.ExtraBold,
                            letterSpacing = 6.sp, color = x.accentA
                        )
                        Text(
                            "Партнёр введёт его у себя. Вы уже внутри.",
                            textAlign = TextAlign.Center,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(Modifier.height(12.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            GhostButton("Копировать", { clipboard.setText(AnnotatedString(c)) }, Modifier.weight(1f))
                            PrimaryButton(
                                "Войти",
                                { myUid?.let { onDone(it, LocalProfile(avatarUrl, birth, since)) } },
                                Modifier.weight(1f)
                            )
                        }
                    }
                }
            } else {
                CjField(
                    code, { code = it.uppercase() }, "Код партнёра",
                    keyboard = KeyboardOptions(capitalization = androidx.compose.ui.text.input.KeyboardCapitalization.Characters)
                )
                Spacer(Modifier.height(12.dp))
                PrimaryButton(
                    if (busy) "Входим…" else "Присоединиться",
                    {
                        scope.launch {
                            busy = true
                            try {
                                val av = avatarUri?.let { uploadImage(ctx, it) } ?: ""
                                val uid = ApiClient.api.join(JoinReq(name, code, birth, av)).user_id
                                onDone(uid, LocalProfile(av, birth, since))
                            } catch (e: Exception) { vm.error = e.message }
                            busy = false
                        }
                    },
                    Modifier.fillMaxWidth(),
                    enabled = name.isNotBlank() && code.isNotBlank() && since.isNotBlank() && !busy
                )
            }
            Err(vm)
        }
    }
}

// ---------- главная ----------
@Composable
private fun HeroPerson(
    name: String, photo: String?, birthText: String?, dim: Boolean, onClick: () -> Unit
) {
    Column(Modifier.width(112.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.clip(CircleShape).clickable(onClick = onClick)) {
            Avatar(name, 72.dp, dim, photo)
        }
        Spacer(Modifier.height(6.dp))
        Text(
            name, color = Color.White, fontWeight = FontWeight.Bold, maxLines = 1,
            style = MaterialTheme.typography.titleMedium
        )
        if (birthText != null) {
            Text(
                birthText, color = Color.White.copy(alpha = 0.85f),
                style = MaterialTheme.typography.labelMedium, maxLines = 1
            )
        }
    }
}

@Composable
fun HomeScreen(
    vm: AppVm, profile: LocalProfile,
    toQuizzes: () -> Unit, onWidgetSend: () -> Unit, onProfile: () -> Unit
) {
    val uid = vm.userId ?: return
    var me by remember { mutableStateOf<MeResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({ loading = it }, { ApiClient.api.me(uid) }) { me = it }
    LaunchedEffect(uid) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader(
                    me?.let { "Привет, ${it.name}" } ?: "CoupleJoy",
                    "Ваше пространство для двоих"
                )
                Err(vm)
            }
        }
        if (loading && me == null) item { HeartLoader() }
        me?.let { m ->
            item {
                Appear(0) {
                    val days = daysTogether(profile.since, m.days_together)
                    var shown by remember { mutableStateOf(0) }
                    LaunchedEffect(days) {
                        animate(0f, days.toFloat(), animationSpec = tween(1200)) { v, _ -> shown = v.toInt() }
                    }
                    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.Top
                        ) {
                            HeroPerson(
                                m.name, profile.avatar, birthLine(profile.birth), false, onProfile
                            )
                            Icon(
                                Icons.Rounded.Favorite, null, tint = Color.White,
                                modifier = Modifier.padding(top = 24.dp, start = 6.dp, end = 6.dp).size(26.dp)
                            )
                            HeroPerson(
                                m.partner?.name ?: "Ждём…", m.partner?.avatar,
                                m.partner?.let { birthLine(it.birth, it.age) },
                                m.partner == null, onProfile
                            )
                        }
                        Spacer(Modifier.height(16.dp))
                        Text(
                            "$shown", color = Color.White, fontSize = 60.sp,
                            fontWeight = FontWeight.ExtraBold, modifier = Modifier.fillMaxWidth(),
                            textAlign = TextAlign.Center
                        )
                        Text(
                            "дней вместе", color = Color.White.copy(alpha = 0.9f),
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center
                        )
                        if (profile.since.isNotBlank()) {
                            Text(
                                "с ${prettyDate(profile.since)}", color = Color.White.copy(alpha = 0.8f),
                                style = MaterialTheme.typography.labelMedium,
                                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center
                            )
                        }
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                            Text(
                                "🔥 Серия: ${m.streak}",
                                Modifier.clip(RoundedCornerShape(50)).background(Color.White.copy(alpha = 0.22f))
                                    .padding(horizontal = 14.dp, vertical = 6.dp),
                                color = Color.White, style = MaterialTheme.typography.labelLarge
                            )
                        }
                    }
                }
            }
            if (profile.since.isBlank()) {
                item {
                    Appear(1) {
                        SoftCard(Modifier.fillMaxWidth(), onClick = onProfile, padding = 16.dp) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                IconBadge(Icons.Rounded.Favorite)
                                Spacer(Modifier.width(14.dp))
                                Column(Modifier.weight(1f)) {
                                    Text("Выберите дату начала отношений", style = MaterialTheme.typography.titleMedium)
                                    Text(
                                        "Счётчик дней будет расти каждый день",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                                Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
            item {
                Appear(1) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Text("Настроение", style = MaterialTheme.typography.titleLarge)
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            MoodBox("Вы", m.my_mood?.mood, m.my_mood?.note, Modifier.weight(1f))
                            MoodBox("Партнёр", m.partner_mood?.mood, m.partner_mood?.note, Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(16.dp))
                        SectionLabel("Как вы сейчас?")
                        Spacer(Modifier.height(8.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            listOf("😍", "🥰", "😊", "😢", "😡").forEach { e ->
                                EmojiButton(e, m.my_mood?.mood == e) {
                                    scope.launch {
                                        try {
                                            ApiClient.api.mood(MoodReq(uid, e))
                                            reload()
                                        } catch (ex: Exception) { vm.error = ex.message }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            item {
                Appear(2) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                        ActionTile(
                            Modifier.weight(1f), Icons.Rounded.Quiz,
                            "Викторины", "Проверьте совместимость", toQuizzes
                        )
                        ActionTile(
                            Modifier.weight(1f), Icons.Rounded.PhotoCamera,
                            "Фото партнёру", "На его виджет", onWidgetSend
                        )
                    }
                }
            }
        }
    }
}

// ---------- профиль ----------
@Composable
fun ProfileScreen(
    vm: AppVm, profile: LocalProfile,
    onSave: (LocalProfile) -> Unit, onBack: () -> Unit
) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var me by remember { mutableStateOf<MeResp?>(null) }
    var busy by remember { mutableStateOf(false) }
    LaunchedEffect(uid) { vm.io({}, { ApiClient.api.me(uid) }) { me = it } }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { u ->
        if (u != null) scope.launch {
            busy = true
            try { onSave(profile.copy(avatar = uploadImage(ctx, u))) }
            catch (e: Exception) { vm.error = e.message }
            busy = false
        }
    }
    val days = daysTogether(profile.since, me?.days_together ?: 0)
    ListScreen {
        item {
            Column {
                ScreenHeader("Профиль", null, onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth(), padding = 22.dp) {
                    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            Modifier.size(128.dp).clip(CircleShape).background(x.brand())
                                .clickable { pick.launch("image/*") },
                            Alignment.Center
                        ) {
                            Avatar(me?.name ?: "?", 128.dp, photo = profile.avatar)
                        }
                        Spacer(Modifier.height(10.dp))
                        Text(me?.name ?: "…", style = MaterialTheme.typography.titleLarge)
                        birthLine(profile.birth)?.let {
                            Text(it, style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Spacer(Modifier.height(12.dp))
                        GhostButton(
                            if (busy) "Загружаем…" else if (profile.avatar.isBlank()) "Добавить фото" else "Сменить фото",
                            { if (!busy) pick.launch("image/*") },
                            icon = Icons.Rounded.PhotoCamera
                        )
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    DateField("Дата рождения", profile.birth, { onSave(profile.copy(birth = it)) })
                    Spacer(Modifier.height(12.dp))
                    DateField("Вместе с…", profile.since, { onSave(profile.copy(since = it)) })
                    Spacer(Modifier.height(14.dp))
                    Text(
                        "Дней вместе: $days", style = MaterialTheme.typography.titleMedium, color = x.accentA
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "Число растёт само каждый день. Изменения профиля сохраняются на этом устройстве; партнёр видит фото и дату рождения, указанные при входе.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
private fun MoodBox(label: String, mood: String?, note: String?, modifier: Modifier) {
    Column(
        modifier.clip(RoundedCornerShape(20.dp))
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.06f))
            .padding(vertical = 14.dp, horizontal = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(mood ?: "—", fontSize = 40.sp)
        Text(
            note.orEmpty(), style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center, maxLines = 2
        )
    }
}

@Composable
private fun EmojiButton(e: String, selected: Boolean, onClick: () -> Unit) {
    val x = LocalCj.current
    val s by animateFloatAsState(if (selected) 1.14f else 1f, label = "emo")
    val src = remember { MutableInteractionSource() }
    Box(
        Modifier.size(56.dp).graphicsLayer { scaleX = s; scaleY = s }.pressScale(src, 0.88f)
            .clip(CircleShape)
            .background(if (selected) x.accentA.copy(alpha = 0.25f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.06f), CircleShape)
            .border(if (selected) 2.dp else 0.dp, if (selected) x.accentA else Color.Transparent, CircleShape)
            .clickable(src, null, onClick = onClick),
        Alignment.Center
    ) { Text(e, fontSize = 28.sp) }
}

// ---------- ежедневный вопрос ----------
@Composable
fun DailyScreen(vm: AppVm, toQuizzes: () -> Unit, onPacks: () -> Unit) {
    val uid = vm.userId ?: return
    var d by remember { mutableStateOf<DailyResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    var text by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({ loading = it }, { ApiClient.api.daily(uid) }) { d = it }
    LaunchedEffect(uid) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader("Вопрос дня", "Отвечайте честно — и узнавайте друг друга лучше")
                Err(vm)
            }
        }
        if (loading && d == null) item { HeartLoader() }
        d?.let { dd ->
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
                        Text(
                            "ВОПРОС ДНЯ • ${dd.question.date}",
                            color = Color.White.copy(alpha = 0.85f),
                            style = MaterialTheme.typography.labelMedium
                        )
                        Spacer(Modifier.height(10.dp))
                        Text(
                            dd.question.text, color = Color.White, fontSize = 22.sp,
                            lineHeight = 30.sp, fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
            item {
                Appear(1) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        if (dd.my_answer == null) {
                            CjField(text, { text = it }, "Ваш ответ", singleLine = false, minLines = 3)
                            Spacer(Modifier.height(12.dp))
                            PrimaryButton(
                                "Отправить",
                                {
                                    scope.launch {
                                        try {
                                            ApiClient.api.answer(AnswerReq(uid, text))
                                            text = ""
                                            reload()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                },
                                Modifier.fillMaxWidth(), enabled = text.isNotBlank(),
                                icon = Icons.AutoMirrored.Rounded.Send
                            )
                        } else {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Bubble("Вы", dd.my_answer, mine = true)
                                if (dd.partner_answer != null) Bubble("Партнёр", dd.partner_answer, mine = false)
                                else WaitingBubble("Партнёр ещё отвечает…")
                            }
                        }
                    }
                }
            }
            item {
                Appear(2) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                        ActionTile(Modifier.weight(1f), Icons.Rounded.Quiz, "Викторины", "Игры для двоих", toQuizzes)
                        ActionTile(Modifier.weight(1f), Icons.Rounded.Style, "Темы вопросов", "Глубокие разговоры", onPacks)
                    }
                }
            }
        }
    }
}

// ---------- викторины ----------
@Composable
fun QuizListScreen(vm: AppVm, open: (Int) -> Unit, onBack: () -> Unit) {
    var list by remember { mutableStateOf<List<QuizShort>?>(null) }
    LaunchedEffect(Unit) {
        vm.io({}, { ApiClient.api.quizzes() }) { list = it }
    }
    ListScreen {
        item {
            Column {
                ScreenHeader("Викторины", "Сравните, как вы знаете друг друга", onBack)
                Err(vm)
            }
        }
        if (list == null) item { HeartLoader() }
        list?.let { l ->
            if (l.isEmpty()) item { EmptyHint("🎮", "Пока нет викторин") }
            itemsIndexed(l) { i, q ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth(), onClick = { open(q.id) }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconBadge(Icons.Rounded.Quiz)
                            Spacer(Modifier.width(14.dp))
                            Column(Modifier.weight(1f)) {
                                Text(q.title, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    "Вопросов: ${q.questions}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun OptionRow(text: String, selected: Boolean, onClick: () -> Unit) {
    val x = LocalCj.current
    val shape = RoundedCornerShape(16.dp)
    val src = remember { MutableInteractionSource() }
    Row(
        Modifier.fillMaxWidth().pressScale(src, 0.98f).clip(shape)
            .background(if (selected) x.accentA.copy(alpha = 0.16f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f), shape)
            .border(1.5.dp, if (selected) x.accentA else Color.Transparent, shape)
            .clickable(src, null, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier.size(20.dp).clip(CircleShape)
                .border(2.dp, if (selected) x.accentA else MaterialTheme.colorScheme.outline, CircleShape),
            Alignment.Center
        ) {
            if (selected) Box(Modifier.size(10.dp).clip(CircleShape).background(x.accentA))
        }
        Spacer(Modifier.width(12.dp))
        Text(text, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
fun QuizScreen(vm: AppVm, id: Int, back: () -> Unit) {
    val uid = vm.userId ?: return
    var q by remember { mutableStateOf<QuizResp?>(null) }
    var res by remember { mutableStateOf<QuizResult?>(null) }
    val scope = rememberCoroutineScope()
    fun reload() {
        vm.io({}, { ApiClient.api.quiz(id, uid) }) { q = it }
        vm.io({}, { ApiClient.api.quizResult(id, uid) }) { res = it }
    }
    LaunchedEffect(id) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader(q?.title ?: "…", "Отвечайте — партнёр ответит отдельно", back)
                Err(vm)
            }
        }
        if (q == null) item { HeartLoader() }
        res?.let {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (it.compatibility != null) {
                                RingProgress(it.compatibility / 100f, "${it.compatibility}%", "совместимость")
                            } else {
                                val f = if (it.total > 0) it.answered_together / it.total.toFloat() else 0f
                                RingProgress(f, "${it.answered_together}/${it.total}", "вместе")
                            }
                            Spacer(Modifier.width(16.dp))
                            Column(Modifier.weight(1f)) {
                                Text(
                                    if (it.compatibility == null) "Ответьте оба — увидите результат"
                                    else "Совместимость: ${it.compatibility}%",
                                    style = MaterialTheme.typography.titleMedium
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "Вместе отвечено: ${it.answered_together}/${it.total}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
        q?.questions?.let { qs ->
            itemsIndexed(qs) { i, qq ->
                Appear(i + 1) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                            Text(
                                "${i + 1}. ${qq.text}", style = MaterialTheme.typography.titleMedium,
                                modifier = Modifier.weight(1f)
                            )
                            if (qq.partner_answered) {
                                Spacer(Modifier.width(8.dp))
                                Text("💜", fontSize = 20.sp)
                            }
                        }
                        Spacer(Modifier.height(10.dp))
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            qq.options.forEachIndexed { oi, opt ->
                                OptionRow(opt, qq.my_option == oi) {
                                    scope.launch {
                                        try {
                                            ApiClient.api.quizAnswer(id, QuizAnsReq(uid, qq.id, oi))
                                            reload()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- идеи ----------
@Composable
fun IdeasScreen(vm: AppVm) {
    val x = LocalCj.current
    var list by remember { mutableStateOf<List<Idea>?>(null) }
    var lucky by remember { mutableStateOf<Idea?>(null) }
    var title by remember { mutableStateOf("") }
    var filter by remember { mutableStateOf(0) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.ideas() }) { list = it }
    LaunchedEffect(Unit) { reload() }
    val shown = list?.filter {
        when (filter) { 1 -> it.done != 1; 2 -> it.done == 1; else -> true }
    }
    ListScreen {
        item {
            Column {
                ScreenHeader("Идеи свиданий", "Выбирайте, что попробовать вместе")
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 20.dp) {
                    val l = lucky
                    if (l == null) {
                        Text(
                            "Не знаете, куда пойти?", color = Color.White,
                            style = MaterialTheme.typography.titleLarge
                        )
                        Text(
                            "Пусть выберет случай 🎲", color = Color.White.copy(alpha = 0.9f),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    } else {
                        Text(l.title, color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "${l.category} • ${l.budget}", color = Color.White.copy(alpha = 0.9f),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    Row(
                        Modifier.clip(RoundedCornerShape(16.dp)).background(Color.White)
                            .clickable {
                                scope.launch {
                                    try { lucky = ApiClient.api.ideaRandom() }
                                    catch (e: Exception) { vm.error = e.message }
                                }
                            }
                            .padding(horizontal = 18.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Rounded.Casino, null, tint = x.accentA, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(8.dp))
                        Text("Мне повезёт", color = x.accentA, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Своя идея", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    CjField(title, { title = it }, "Что хотите попробовать?")
                    Spacer(Modifier.height(10.dp))
                    PrimaryButton(
                        "Добавить",
                        {
                            scope.launch {
                                try {
                                    ApiClient.api.ideaAdd(IdeaReq(title))
                                    title = ""
                                    reload()
                                } catch (e: Exception) { vm.error = e.message }
                            }
                        },
                        Modifier.fillMaxWidth(), enabled = title.isNotBlank(), icon = Icons.Rounded.Add
                    )
                }
            }
        }
        item { Segmented(listOf("Все", "Ждут нас", "Сделано"), filter) { filter = it } }
        if (list == null) item { HeartLoader() }
        shown?.let { s ->
            if (s.isEmpty()) item { EmptyHint("💡", "Здесь пока пусто") }
            itemsIndexed(s) { i, idea ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth(), padding = 16.dp) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    idea.title,
                                    style = MaterialTheme.typography.titleMedium.copy(
                                        textDecoration = if (idea.done == 1) TextDecoration.LineThrough else TextDecoration.None
                                    ),
                                    color = if (idea.done == 1) MaterialTheme.colorScheme.onSurfaceVariant
                                    else MaterialTheme.colorScheme.onSurface
                                )
                                Spacer(Modifier.height(6.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    if (idea.category.isNotBlank()) Pill(idea.category, x.accentB)
                                    if (idea.budget.isNotBlank()) Pill(idea.budget, MaterialTheme.colorScheme.tertiary)
                                }
                            }
                            Spacer(Modifier.width(10.dp))
                            CheckCircle(idea.done == 1) {
                                scope.launch {
                                    try {
                                        ApiClient.api.ideaDone(idea.id, idea.done != 1)
                                        reload()
                                    } catch (e: Exception) { vm.error = e.message }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- журнал ----------
@Composable
fun JournalScreen(vm: AppVm) {
    val uid = vm.userId ?: return
    var list by remember { mutableStateOf<List<JournalEntry>?>(null) }
    var title by remember { mutableStateOf("") }
    var text by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.journal(uid) }) { list = it }
    LaunchedEffect(uid) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader("Общий журнал", "Моменты, которые хочется сохранить")
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Новый момент", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    CjField(title, { title = it }, "Заголовок момента")
                    Spacer(Modifier.height(10.dp))
                    CjField(text, { text = it }, "Что запомнилось?", singleLine = false, minLines = 3)
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        "Сохранить момент",
                        {
                            scope.launch {
                                try {
                                    ApiClient.api.journalAdd(JournalReq(uid, title, text))
                                    title = ""; text = ""
                                    reload()
                                } catch (e: Exception) { vm.error = e.message }
                            }
                        },
                        Modifier.fillMaxWidth(), enabled = title.isNotBlank()
                    )
                }
            }
        }
        if (list == null) item { HeartLoader() }
        list?.let { l ->
            if (l.isEmpty()) item { EmptyHint("📖", "Запишите ваш первый общий момент") }
            itemsIndexed(l) { i, j ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row {
                            Box(Modifier.clip(CircleShape).background(LocalCj.current.brand())) {
                                Avatar(j.author, 40.dp)
                            }
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(j.title, style = MaterialTheme.typography.titleMedium)
                                if (j.text.isNotBlank()) {
                                    Spacer(Modifier.height(4.dp))
                                    Text(j.text, style = MaterialTheme.typography.bodyLarge)
                                }
                                Spacer(Modifier.height(8.dp))
                                Text(
                                    "${j.author} • ${j.ts}",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.secondary
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- темы вопросов ----------
@Composable
fun PackListScreen(vm: AppVm, open: (Int) -> Unit, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    var list by remember { mutableStateOf<List<PackShort>?>(null) }
    LaunchedEffect(uid) { vm.io({}, { ApiClient.api.packs(uid) }) { list = it } }
    ListScreen {
        item {
            Column {
                ScreenHeader("Темы вопросов", "Ответ партнёра виден, когда ответили оба.", onBack)
                Err(vm)
            }
        }
        if (list == null) item { HeartLoader() }
        list?.let { l ->
            if (l.isEmpty()) item { EmptyHint("📚", "Пока нет тем") }
            itemsIndexed(l) { i, p ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth(), onClick = { open(p.id) }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(p.title, style = MaterialTheme.typography.titleMedium)
                                if (p.description.isNotBlank()) {
                                    Text(
                                        p.description, style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                            Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Spacer(Modifier.height(12.dp))
                        ProgressBar(if (p.total > 0) p.answered_by_me / p.total.toFloat() else 0f)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Ваших: ${p.answered_by_me}/${p.total} • Вместе: ${p.answered_together}",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun PackScreen(vm: AppVm, id: Int, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    var p by remember { mutableStateOf<PackResp?>(null) }
    var drafts by remember { mutableStateOf<Map<Int, String>>(emptyMap()) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.pack(id, uid) }) { p = it }
    LaunchedEffect(id) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader(p?.title ?: "…", p?.description?.ifBlank { null }, onBack)
                Err(vm)
            }
        }
        if (p == null) item { HeartLoader() }
        p?.questions?.let { qs ->
            itemsIndexed(qs) { i, q ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                            Text(q.text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                            if (q.partner_answered) {
                                Spacer(Modifier.width(8.dp))
                                Text("💜", fontSize = 20.sp)
                            }
                        }
                        Spacer(Modifier.height(12.dp))
                        if (q.my_answer == null) {
                            CjField(
                                drafts[q.id] ?: "", { drafts = drafts + (q.id to it) },
                                "Ваш ответ", singleLine = false, minLines = 2
                            )
                            Spacer(Modifier.height(10.dp))
                            PrimaryButton(
                                "Отправить",
                                {
                                    scope.launch {
                                        try {
                                            ApiClient.api.packAnswer(id, PackAnsReq(uid, q.id, drafts[q.id] ?: ""))
                                            reload()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                },
                                Modifier.fillMaxWidth(), enabled = !(drafts[q.id].isNullOrBlank()),
                                icon = Icons.AutoMirrored.Rounded.Send
                            )
                        } else {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Bubble("Вы", q.my_answer, mine = true)
                                if (q.partner_answer != null) Bubble("Партнёр", q.partner_answer, mine = false)
                                else WaitingBubble("Партнёр ещё отвечает…")
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- «Ещё» ----------
@Composable
fun MoreScreen(
    onProfile: () -> Unit, onQuizzes: () -> Unit, onPacks: () -> Unit,
    onEvents: () -> Unit, onWidget: () -> Unit, onSettings: () -> Unit
) {
    @Composable
    fun MenuRow(i: Int, icon: androidx.compose.ui.graphics.vector.ImageVector, t: String, s: String, c: () -> Unit) {
        Appear(i) {
            SoftCard(Modifier.fillMaxWidth(), onClick = c, padding = 16.dp) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconBadge(icon)
                    Spacer(Modifier.width(14.dp))
                    Column(Modifier.weight(1f)) {
                        Text(t, style = MaterialTheme.typography.titleMedium)
                        Text(s, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
    ListScreen {
        item { ScreenHeader("Ещё", "Все разделы CoupleJoy") }
        item { MenuRow(0, Icons.Rounded.Person, "Профиль", "Фото, дата рождения, дата начала отношений", onProfile) }
        item { MenuRow(1, Icons.Rounded.Quiz, "Викторины", "Совместимость и игры", onQuizzes) }
        item { MenuRow(2, Icons.Rounded.Style, "Темы вопросов", "Разговоры по душам", onPacks) }
        item { MenuRow(3, Icons.Rounded.HourglassTop, "Обратный отсчёт", "Годовщины и поездки", onEvents) }
        item { MenuRow(4, Icons.Rounded.PhotoCamera, "Фото на виджет", "Порадуйте партнёра", onWidget) }
        item { MenuRow(5, Icons.Rounded.Settings, "Настройки", "Тема, сервер, выход", onSettings) }
    }
}

// ---------- настройки ----------
@Composable
fun SettingsScreen(
    vm: AppVm, baseUrl: String, dark: Boolean,
    onDark: (Boolean) -> Unit,
    onSaveUrl: (String) -> Unit, onLogout: () -> Unit, onBack: () -> Unit
) {
    val x = LocalCj.current
    var url by remember(baseUrl) { mutableStateOf(baseUrl) }
    var saved by remember { mutableStateOf(false) }
    ListScreen {
        item {
            Column {
                ScreenHeader("Настройки", null, onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconBadge(if (dark) Icons.Rounded.DarkMode else Icons.Rounded.LightMode)
                        Spacer(Modifier.width(14.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Тёмная тема", style = MaterialTheme.typography.titleMedium)
                            Text(
                                if (dark) "Включена" else "Выключена",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(
                            dark, onDark,
                            colors = SwitchDefaults.colors(
                                checkedTrackColor = x.accentA, checkedThumbColor = Color.White
                            )
                        )
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconBadge(Icons.Rounded.Cloud)
                        Spacer(Modifier.width(14.dp))
                        Text("Адрес сервера", style = MaterialTheme.typography.titleMedium)
                    }
                    Spacer(Modifier.height(10.dp))
                    Text(
                        "По умолчанию: https://ssssw-sladaqqq.amvera.io/  •  Эмулятор: http://10.0.2.2:8000/  •  Домашний Wi-Fi: http://192.168.1.81:8000/",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(12.dp))
                    CjField(url, { url = it; saved = false }, "http(s)://…")
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        "Сохранить",
                        {
                            onSaveUrl(if (url.endsWith("/")) url else "$url/")
                            saved = true
                        },
                        Modifier.fillMaxWidth()
                    )
                    if (saved) {
                        Spacer(Modifier.height(8.dp))
                        Text("Сохранено ✅", color = x.good, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
        item { Appear(2) { LocationShareCard(vm) } }
        item {
            Appear(3) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Виджет на рабочий стол", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Долгое нажатие по рабочему столу → Виджеты → CoupleJoy. Обновляется сам каждые 15 минут, показывает дни, настроение и фото партнёра.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
        item {
            Appear(4) {
                GhostButton(
                    "Выйти из пары на этом устройстве", onLogout,
                    Modifier.fillMaxWidth(), icon = Icons.AutoMirrored.Rounded.Logout
                )
            }
        }
    }
}

// ---------- фото на виджет ----------
@Composable
fun WidgetSendScreen(vm: AppVm, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var uri by remember { mutableStateOf<Uri?>(null) }
    var caption by remember { mutableStateOf("") }
    var msg by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var mine by remember { mutableStateOf<WidgetPhoto?>(null) }
    var theirs by remember { mutableStateOf<WidgetPhoto?>(null) }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {
        uri = it
    }
    fun reload() = vm.io({}, { ApiClient.api.widget(uid) }) {
        mine = it.mine
        theirs = it.partner
    }
    LaunchedEffect(uid) { reload() }
    val base = ctx.getSharedPreferences("cj", Context.MODE_PRIVATE)
        .getString("base_url", ApiClient.DEFAULT_URL)!!.trimEnd('/')
    ListScreen {
        item {
            Column {
                ScreenHeader("На виджет партнёра", "Фото сразу появится на домашнем экране партнёра.", onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    val shape = RoundedCornerShape(22.dp)
                    Box(
                        Modifier.fillMaxWidth().height(230.dp).clip(shape)
                            .background(x.accentA.copy(alpha = 0.08f), shape)
                            .border(1.5.dp, x.accentA.copy(alpha = 0.4f), shape)
                            .clickable { pick.launch("image/*") },
                        Alignment.Center
                    ) {
                        val u = uri
                        if (u == null) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(Icons.Rounded.PhotoCamera, null, tint = x.accentA, modifier = Modifier.size(40.dp))
                                Spacer(Modifier.height(8.dp))
                                Text("Выбрать фото", color = x.accentA, style = MaterialTheme.typography.titleMedium)
                            }
                        } else {
                            AsyncImage(u, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                        }
                    }
                    if (uri != null) {
                        Spacer(Modifier.height(10.dp))
                        GhostButton("Выбрать другое", { pick.launch("image/*") }, Modifier.fillMaxWidth())
                    }
                    Spacer(Modifier.height(12.dp))
                    CjField(caption, { caption = it }, "Подпись (необязательно)")
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        if (sending) "Отправляем…" else "Отправить на виджет 💞",
                        {
                            scope.launch {
                                sending = true
                                try {
                                    val url = uploadImage(ctx, uri!!)
                                    ApiClient.api.widgetSend(WidgetReq(uid, url, caption))
                                    uri = null
                                    caption = ""
                                    msg = "Отправлено! 💞"
                                    reload()
                                } catch (e: Exception) {
                                    vm.error = e.message
                                }
                                sending = false
                            }
                        },
                        Modifier.fillMaxWidth(), enabled = uri != null && !sending
                    )
                    if (msg.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text(msg, color = x.good, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Фото партнёра вам", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    val t = theirs
                    if (t != null) {
                        AsyncImage(
                            base + t.photo, null,
                            Modifier.fillMaxWidth().height(240.dp).clip(RoundedCornerShape(20.dp)),
                            contentScale = ContentScale.Crop
                        )
                        if (t.caption.isNotBlank()) {
                            Spacer(Modifier.height(8.dp))
                            Text(t.caption, style = MaterialTheme.typography.bodyLarge)
                        }
                    } else {
                        Text(
                            "Пока ничего нет", style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

// ---------- события ----------
@Composable
fun EventsScreen(vm: AppVm, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    var list by remember { mutableStateOf<List<EventResp>?>(null) }
    var title by remember { mutableStateOf("") }
    var date by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.events(uid) }) { list = it }
    LaunchedEffect(uid) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader("Обратный отсчёт", "До самых важных дат", onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Новое событие", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    CjField(title, { title = it }, "Событие (годовщина, поездка…)")
                    Spacer(Modifier.height(10.dp))
                    CjField(
                        date, { date = it }, "Дата ГГГГ-ММ-ДД",
                        keyboard = KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                    )
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        "Добавить",
                        {
                            scope.launch {
                                try {
                                    ApiClient.api.eventAdd(EventReq(uid, title, date))
                                    title = ""; date = ""
                                    reload()
                                } catch (e: Exception) { vm.error = e.message }
                            }
                        },
                        Modifier.fillMaxWidth(), enabled = title.isNotBlank() && date.isNotBlank(),
                        icon = Icons.Rounded.Add
                    )
                }
            }
        }
        if (list == null) item { HeartLoader() }
        list?.let { l ->
            if (l.isEmpty()) item { EmptyHint("⏳", "Добавьте первую важную дату") }
            itemsIndexed(l) { i, e ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth(), padding = 16.dp) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val past = e.days_left < 0
                            Column(
                                Modifier.size(72.dp).clip(RoundedCornerShape(20.dp))
                                    .then(
                                        if (past) Modifier.background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.10f))
                                        else Modifier.background(x.brand())
                                    ),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                Text(
                                    "${if (past) -e.days_left else e.days_left}",
                                    fontSize = 26.sp, fontWeight = FontWeight.ExtraBold,
                                    color = if (past) MaterialTheme.colorScheme.onSurfaceVariant else Color.White
                                )
                                Text(
                                    "дн.", fontSize = 11.sp,
                                    color = if (past) MaterialTheme.colorScheme.onSurfaceVariant else Color.White.copy(alpha = 0.9f)
                                )
                            }
                            Spacer(Modifier.width(14.dp))
                            Column(Modifier.weight(1f)) {
                                Text(e.title, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    if (e.days_left >= 0) "Осталось дней: ${e.days_left}"
                                    else "Было ${-e.days_left} дн. назад",
                                    style = MaterialTheme.typography.bodyMedium
                                )
                                Text(
                                    e.date, style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.secondary
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
