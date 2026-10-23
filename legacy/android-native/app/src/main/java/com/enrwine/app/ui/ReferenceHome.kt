package com.enrwine.app.ui

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Casino
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material.icons.rounded.Quiz
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.TrackChanges
import androidx.compose.material3.Icon
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.enrwine.app.AppVm
import com.enrwine.app.api.ActivityResp
import com.enrwine.app.api.ApiClient
import com.enrwine.app.api.DailyResp
import com.enrwine.app.api.MeResp
import com.enrwine.app.api.MoodReq
import com.enrwine.app.api.WidgetResp
import kotlinx.coroutines.launch

private val RefRose = Color(0xFFD94E70)
private val RefInk = Color(0xFF30252B)
private val RefMuted = Color(0xFF85737C)
private val RefCanvas = Color(0xFFFFF9F7)

private fun moodText(mood: String, note: String): String {
    if (note.isNotBlank()) return "$mood  $note"
    val label = when (mood) {
        "🥰" -> "Любовь и нежность"
        "😊" -> "Всё хорошо"
        "😌" -> "Спокойное"
        "😔" -> "Немного грустно"
        else -> "Настроение отмечено"
    }
    return "$mood  $label"
}

@Composable
private fun RefSectionTitle(title: String, action: String? = null, onAction: () -> Unit = {}) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(title, color = RefInk, fontSize = 20.sp, fontWeight = FontWeight.Bold,
            modifier = Modifier.weight(1f))
        if (action != null) {
            Text(action, color = RefRose, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                modifier = Modifier.clip(RoundedCornerShape(14.dp)).clickable(onClick = onAction)
                    .padding(horizontal = 8.dp, vertical = 5.dp))
        }
    }
}

@Composable
private fun RefQuickTile(
    modifier: Modifier,
    icon: ImageVector,
    iconColor: Color,
    background: Color,
    title: String,
    detail: String,
    onClick: () -> Unit
) {
    Column(
        modifier.height(132.dp).clip(RoundedCornerShape(24.dp)).background(background)
            .clickable(onClick = onClick).padding(15.dp),
        verticalArrangement = Arrangement.spacedBy(7.dp)
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(42.dp).clip(RoundedCornerShape(14.dp))
                .background(Color.White.copy(alpha = 0.72f)), Alignment.Center) {
                Icon(icon, null, tint = iconColor, modifier = Modifier.size(27.dp))
            }
            Spacer(Modifier.weight(1f))
            Text("→", color = iconColor, fontWeight = FontWeight.Bold, fontSize = 20.sp)
        }
        Text(title.replace("\n", " "), color = RefInk, fontSize = 15.sp, lineHeight = 18.sp,
            fontWeight = FontWeight.Bold, maxLines = 2)
        Text(detail.replace("\n", " "), color = RefMuted, fontSize = 11.sp,
            lineHeight = 14.sp, maxLines = 2)
    }
}

@Composable
private fun RefMemory(modifier: Modifier, photo: String?, date: String, fallback: Color) {
    Box(modifier.height(126.dp).clip(RoundedCornerShape(18.dp)).background(fallback)) {
        if (!photo.isNullOrBlank()) {
            AsyncImage(photo, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        } else {
            Box(Modifier.fillMaxSize().background(Brush.linearGradient(
                listOf(fallback, Color(0xFF6F4552)))))
            Text("♥", color = Color.White.copy(alpha = 0.75f), fontSize = 30.sp,
                modifier = Modifier.align(Alignment.Center))
        }
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(
            listOf(Color.Transparent, Color.Transparent, Color.Black.copy(alpha = 0.65f)))))
        Text(date, color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.SemiBold,
            modifier = Modifier.align(Alignment.BottomStart).padding(11.dp), maxLines = 1)
    }
}

@Composable
private fun RefStat(
    modifier: Modifier,
    icon: String,
    value: String,
    label: String,
    color: Color
) {
    Row(
        modifier.height(78.dp).clip(RoundedCornerShape(20.dp)).background(Color.White)
            .padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(38.dp).clip(CircleShape).background(color.copy(alpha = 0.12f)),
            Alignment.Center) { Text(icon, fontSize = 20.sp, color = color) }
        Spacer(Modifier.width(10.dp))
        Column {
            Text(value, color = RefInk, fontSize = 15.sp, fontWeight = FontWeight.Bold, maxLines = 1)
            Text(label, color = RefMuted, fontSize = 10.sp, lineHeight = 13.sp, maxLines = 2)
        }
    }
}

@Composable
fun HomeScreen(
    vm: AppVm,
    toQuizzes: () -> Unit,
    onWidgetSend: () -> Unit,
    onProfile: () -> Unit,
    onIdeas: () -> Unit = {},
    onEvents: () -> Unit = {},
    onNotifications: () -> Unit = {},
    onSettings: () -> Unit = {}
) {
    val uid = vm.userId ?: return
    val prefs = LocalContext.current.getSharedPreferences("enrwine", Context.MODE_PRIVATE)
    val base = prefs.getString("base_url", ApiClient.DEFAULT_URL)!!.trimEnd('/')
    var me by remember { mutableStateOf<MeResp?>(null) }
    var photos by remember { mutableStateOf<WidgetResp?>(null) }
    var daily by remember { mutableStateOf<DailyResp?>(null) }
    var activity by remember { mutableStateOf<ActivityResp?>(null) }
    var unreadActivity by remember { mutableStateOf(0) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    fun loadActivity() = scope.launch {
        try {
            val result = ApiClient.api.activity(uid)
            activity = result
            val seen = prefs.getString("activity_seen_$uid", "").orEmpty()
            unreadActivity = result.items.count { it.ts > seen }
        } catch (_: Exception) {
            // Старый сервер без /activity не должен мешать загрузке главного экрана.
        }
    }

    fun reload() = vm.io({ loading = it }, { ApiClient.api.me(uid) }) {
        me = it
        vm.io({}, { ApiClient.api.widget(uid) }) { photos = it }
        vm.io({}, { ApiClient.api.daily(uid) }) { daily = it }
        loadActivity()
    }
    LaunchedEffect(uid) { reload() }

    val mine = photos?.mine?.photo?.takeIf { it.isNotBlank() }?.let { base + it }
    val partner = photos?.partner?.photo?.takeIf { it.isNotBlank() }?.let { base + it }
    val cover = "https://images.unsplash.com/photo-1501901609772-df0848060b33?w=1200&auto=format&fit=crop"
    val hour = remember { java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY) }
    val greeting = when (hour) {
        in 5..11 -> "Доброе утро"
        in 12..17 -> "Добрый день"
        else -> "Добрый вечер"
    }

    LazyColumn(
        Modifier.fillMaxSize().background(RefCanvas),
        contentPadding = PaddingValues(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Box(Modifier.fillMaxWidth().height(310.dp).background(Color(0xFFE9B8B3))) {
                AsyncImage(cover, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                Box(Modifier.fillMaxSize().background(Brush.horizontalGradient(listOf(
                    Color.White.copy(alpha = 0.80f), Color.White.copy(alpha = 0.18f), Color.Transparent
                ))))
                Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(
                    Color.White.copy(alpha = 0.13f), Color.Transparent,
                    Color(0xFF2B1720).copy(alpha = 0.35f)
                ))))
                Text("Enrwine ♡", color = RefInk, fontSize = 30.sp,
                    fontWeight = FontWeight.Bold, fontFamily = FontFamily.Cursive,
                    modifier = Modifier.align(Alignment.TopStart).padding(start = 18.dp, top = 15.dp))
                Row(Modifier.align(Alignment.TopEnd).padding(14.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(Modifier.size(44.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.92f))
                        .clickable {
                            activity?.items?.firstOrNull()?.ts?.let {
                                prefs.edit().putString("activity_seen_$uid", it).apply()
                            }
                            unreadActivity = 0
                            onNotifications()
                        },
                        Alignment.Center) {
                        Icon(Icons.Rounded.Notifications, "Активность партнёра", tint = RefInk,
                            modifier = Modifier.size(23.dp))
                        if (unreadActivity > 0) {
                            Box(Modifier.size(18.dp).align(Alignment.TopEnd).clip(CircleShape)
                                .background(RefRose), Alignment.Center) {
                                Text(if (unreadActivity > 9) "9+" else unreadActivity.toString(),
                                    color = Color.White, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                    Box(Modifier.size(44.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.92f))
                        .clickable(onClick = onSettings), Alignment.Center) {
                        Icon(Icons.Rounded.Settings, null, tint = RefInk, modifier = Modifier.size(23.dp))
                    }
                }
                Column(Modifier.align(Alignment.TopStart).padding(start = 18.dp, top = 86.dp)) {
                    Text("$greeting, ${me?.name ?: "…"}  ♥", color = RefInk,
                        fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    Text("Как вы сегодня?", color = RefInk, fontSize = 14.sp)
                }
                me?.let { m ->
                    Column(Modifier.align(Alignment.BottomStart).padding(horizontal = 18.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(Modifier.fillMaxWidth().height(64.dp).clip(RoundedCornerShape(22.dp))
                            .background(Color.White.copy(alpha = 0.94f)).padding(horizontal = 12.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            val partner = m.partner
                            Box(Modifier.size(44.dp).clip(CircleShape).background(Color(0xFFFFE2E9)),
                                Alignment.Center) {
                                if (!partner?.avatar.isNullOrBlank()) {
                                    AsyncImage(resolvePhoto(LocalContext.current, partner!!.avatar), null,
                                        Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                                } else {
                                    Text(partner?.name?.take(1)?.uppercase() ?: "?", color = RefRose,
                                        fontSize = 18.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                            Spacer(Modifier.width(11.dp))
                            Column(Modifier.weight(1f)) {
                                Text("Настроение партнёра", color = RefMuted, fontSize = 11.sp)
                                Text(m.partner_mood?.let { moodText(it.mood, it.note) } ?: "Пока не выбрано",
                                    color = RefInk, fontSize = 14.sp, fontWeight = FontWeight.Bold,
                                    maxLines = 1)
                            }
                        }
                        Row(Modifier.fillMaxWidth().height(54.dp).clip(RoundedCornerShape(20.dp))
                            .background(Color(0xFFFFEFF2).copy(alpha = 0.96f)).padding(horizontal = 13.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text("Моё настроение", color = RefMuted, fontSize = 10.sp)
                                Text(m.my_mood?.mood ?: "Выбрать", color = RefInk, fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                                listOf("🥰", "😊", "😌", "😔").forEach { emoji ->
                                    val selected = m.my_mood?.mood == emoji
                                    Box(Modifier.size(34.dp).clip(CircleShape)
                                        .background(if (selected) RefRose.copy(alpha = 0.18f) else Color.White)
                                        .clickable {
                                            scope.launch {
                                                try { ApiClient.api.mood(MoodReq(uid, emoji)); reload() }
                                                catch (e: Exception) { vm.error = e.message }
                                            }
                                        }, Alignment.Center) { Text(emoji, fontSize = 18.sp) }
                                }
                            }
                        }
                    }
                }
            }
        }
        item { Err(vm) }
        if (loading && me == null) item { HeartLoader() }
        me?.let { m ->
            item {
                Row(Modifier.padding(horizontal = 18.dp).fillMaxWidth().height(148.dp)
                    .clip(RoundedCornerShape(26.dp)).background(Color(0xFFFFE9EC))
                    .clickable(onClick = toQuizzes).padding(18.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("♥  Сегодня для нас", color = RefRose, fontSize = 12.sp,
                            fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(9.dp))
                        Text("Скажи партнёру 3 вещи, за которые ты ему благодарен(на).",
                            color = RefInk, fontSize = 17.sp, lineHeight = 21.sp,
                            fontWeight = FontWeight.Bold, maxLines = 3)
                    }
                    Text("💕", fontSize = 42.sp)
                    Spacer(Modifier.width(8.dp))
                    Box(Modifier.size(38.dp).clip(CircleShape).background(RefRose), Alignment.Center) {
                        Text("→", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                    }
                }
            }
            item {
                Column(Modifier.padding(horizontal = 18.dp)) {
                    RefSectionTitle("Для вас двоих")
                    Spacer(Modifier.height(11.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        RefQuickTile(Modifier.weight(1f), Icons.Rounded.Casino, Color(0xFF9B55DE),
                            Color(0xFFF1E7FF), "Случайное свидание", "Идея для особенного вечера", onIdeas)
                        RefQuickTile(Modifier.weight(1f), Icons.Rounded.TrackChanges, Color(0xFF278D86),
                            Color(0xFFE4F5F2), "Важные даты", "Ваши общие события и планы", onEvents)
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        RefQuickTile(Modifier.weight(1f), Icons.Rounded.EmojiEvents, Color(0xFFD99B20),
                            Color(0xFFFFF4D9), "Достижения", "Ваши общие награды", onProfile)
                        RefQuickTile(Modifier.weight(1f), Icons.Rounded.Quiz, Color(0xFF7760D9),
                            Color(0xFFEEE9FF), "Вопросы друг другу", "Узнавайте друг друга глубже", toQuizzes)
                    }
                }
            }
            item {
                Column(Modifier.padding(horizontal = 18.dp).fillMaxWidth()) {
                    RefSectionTitle("Наши воспоминания", "Открыть", onWidgetSend)
                    Spacer(Modifier.height(11.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        RefMemory(Modifier.weight(1f), partner, "♥  От партнёра", Color(0xFFD28C6F))
                        RefMemory(Modifier.weight(1f), mine, "Твоё последнее фото", Color(0xFF8BB5C9))
                    }
                }
            }
            item {
                Row(Modifier.padding(horizontal = 18.dp).fillMaxWidth().height(78.dp)
                    .clip(RoundedCornerShape(22.dp)).background(Brush.horizontalGradient(
                        listOf(Color(0xFFA34579), Color(0xFFD76587))))
                    .clickable(onClick = onIdeas).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Text("⚄", color = Color.White, fontSize = 32.sp)
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Чем займёмся сегодня?", color = Color.White, fontSize = 15.sp,
                            fontWeight = FontWeight.Bold)
                        Text("Новый сценарий свидания уже ждёт вас", color = Color.White.copy(alpha = 0.75f),
                            fontSize = 11.sp)
                    }
                    Text("Открыть  →", color = RefRose, fontSize = 12.sp, fontWeight = FontWeight.Bold,
                        modifier = Modifier.clip(RoundedCornerShape(20.dp)).background(Color.White)
                            .padding(horizontal = 14.dp, vertical = 10.dp))
                }
            }
            item {
                Column(Modifier.padding(horizontal = 18.dp).fillMaxWidth()) {
                    RefSectionTitle("Наши серии")
                    Spacer(Modifier.height(11.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        RefStat(Modifier.weight(1f), "♨", "${m.days_together} дней", "Вместе каждый день", RefRose)
                        RefStat(Modifier.weight(1f), "♥", "${m.streak} дней", "Серия активности", RefRose)
                    }
                    Spacer(Modifier.height(10.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        RefStat(Modifier.weight(1f), "☆", if (daily?.my_answer != null) "Готово" else "Ждёт", "Ответ на сегодня", Color(0xFFD69A1B))
                        RefStat(Modifier.weight(1f), "♟", if (m.partner != null) "На связи" else "Не создана", "Ваша пара", Color(0xFF8B5BC9))
                    }
                }
            }
        }
    }
}
