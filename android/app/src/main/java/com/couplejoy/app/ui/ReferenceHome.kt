package com.couplejoy.app.ui

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
import androidx.compose.material.icons.rounded.CalendarMonth
import androidx.compose.material.icons.rounded.Casino
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.Image
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.DailyResp
import com.couplejoy.app.api.MeResp
import com.couplejoy.app.api.MoodReq
import com.couplejoy.app.api.WidgetResp
import kotlinx.coroutines.launch

private val RefRose = Color(0xFFD94E70)
private val RefInk = Color(0xFF30252B)
private val RefMuted = Color(0xFF85737C)
private val RefCanvas = Color(0xFFFFF9F7)

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
        modifier.height(104.dp).clip(RoundedCornerShape(17.dp)).background(background)
            .clickable(onClick = onClick).padding(10.dp),
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        Icon(icon, null, tint = iconColor, modifier = Modifier.size(20.dp))
        Text(title, color = RefInk, fontSize = 10.sp, lineHeight = 12.sp,
            fontWeight = FontWeight.Bold, maxLines = 2)
        Text(detail, color = RefMuted, fontSize = 8.sp, lineHeight = 10.sp, maxLines = 2)
        Text("→", color = iconColor, fontWeight = FontWeight.Bold,
            modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End, fontSize = 12.sp)
    }
}

@Composable
private fun RefMemory(modifier: Modifier, photo: String?, date: String, fallback: Color) {
    Box(modifier.height(68.dp).clip(RoundedCornerShape(10.dp)).background(fallback)) {
        if (!photo.isNullOrBlank()) {
            AsyncImage(photo, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        } else {
            Box(Modifier.fillMaxSize().background(Brush.linearGradient(
                listOf(fallback, Color(0xFF6F4552)))))
            Text("♥", color = Color.White.copy(alpha = 0.75f), fontSize = 20.sp,
                modifier = Modifier.align(Alignment.Center))
        }
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(
            listOf(Color.Transparent, Color.Transparent, Color.Black.copy(alpha = 0.65f)))))
        Text(date, color = Color.White, fontSize = 7.sp,
            modifier = Modifier.align(Alignment.BottomStart).padding(6.dp), maxLines = 1)
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
        modifier.height(52.dp).clip(RoundedCornerShape(13.dp)).background(Color.White)
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(icon, fontSize = 15.sp, color = color)
        Spacer(Modifier.width(5.dp))
        Column {
            Text(value, color = RefInk, fontSize = 10.sp, fontWeight = FontWeight.Bold, maxLines = 1)
            Text(label, color = RefMuted, fontSize = 7.sp, lineHeight = 9.sp, maxLines = 2)
        }
    }
}

@Composable
fun HomeScreen(
    vm: AppVm,
    profile: LocalProfile,
    toQuizzes: () -> Unit,
    onWidgetSend: () -> Unit,
    onProfile: () -> Unit,
    onIdeas: () -> Unit = {},
    onEvents: () -> Unit = {},
    onSettings: () -> Unit = {}
) {
    val uid = vm.userId ?: return
    val prefs = LocalContext.current.getSharedPreferences("cj", Context.MODE_PRIVATE)
    val base = prefs.getString("base_url", ApiClient.DEFAULT_URL)!!.trimEnd('/')
    var me by remember { mutableStateOf<MeResp?>(null) }
    var photos by remember { mutableStateOf<WidgetResp?>(null) }
    var daily by remember { mutableStateOf<DailyResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    fun reload() = vm.io({ loading = it }, { ApiClient.api.me(uid) }) {
        me = it
        vm.io({}, { ApiClient.api.widget(uid) }) { photos = it }
        vm.io({}, { ApiClient.api.daily(uid) }) { daily = it }
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
        contentPadding = PaddingValues(bottom = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item {
            Box(Modifier.fillMaxWidth().height(196.dp).background(Color(0xFFE9B8B3))) {
                AsyncImage(cover, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(
                    Color.White.copy(alpha = 0.13f), Color.Transparent,
                    Color(0xFF2B1720).copy(alpha = 0.35f)
                ))))
                Text("Enrwine ♡", color = RefInk, fontSize = 27.sp,
                    fontWeight = FontWeight.Bold, fontFamily = FontFamily.Cursive,
                    modifier = Modifier.align(Alignment.TopStart).padding(start = 16.dp, top = 12.dp))
                Row(Modifier.align(Alignment.TopEnd).padding(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.size(34.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.9f)),
                        Alignment.Center) {
                        Icon(Icons.Rounded.Notifications, null, tint = RefInk, modifier = Modifier.size(18.dp))
                        Box(Modifier.size(14.dp).align(Alignment.TopEnd).clip(CircleShape).background(RefRose),
                            Alignment.Center) { Text("3", color = Color.White, fontSize = 8.sp) }
                    }
                    Box(Modifier.size(34.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.9f))
                        .clickable(onClick = onSettings), Alignment.Center) {
                        Icon(Icons.Rounded.Settings, null, tint = RefInk, modifier = Modifier.size(18.dp))
                    }
                }
                Column(Modifier.align(Alignment.CenterStart).padding(start = 16.dp, bottom = 14.dp)) {
                    Text("$greeting, ${me?.name ?: "…"}  ♥", color = RefInk,
                        fontSize = 19.sp, fontWeight = FontWeight.Bold)
                    Text("Как вы сегодня?", color = RefInk, fontSize = 12.sp)
                }
                me?.let { m ->
                    Row(Modifier.align(Alignment.BottomStart).padding(start = 16.dp, end = 150.dp, bottom = 10.dp)
                        .fillMaxWidth().height(48.dp).clip(RoundedCornerShape(18.dp))
                        .background(Color.White.copy(alpha = 0.92f)).clickable(onClick = onProfile)
                        .padding(horizontal = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                        Avatar(m.name, 34.dp, photo = profile.avatar)
                        Spacer(Modifier.width(8.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Моё настроение", color = RefMuted, fontSize = 9.sp)
                            Text(m.my_mood?.let { "${it.mood}  Всё хорошо" } ?: "Выбрать настроение",
                                color = RefInk, fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                        }
                        Text("›", color = RefRose, fontSize = 20.sp)
                    }
                }
            }
        }
        item { Err(vm) }
        if (loading && me == null) item { HeartLoader() }
        me?.let { m ->
            item {
                Row(Modifier.padding(horizontal = 16.dp).fillMaxWidth().height(98.dp)
                    .clip(RoundedCornerShape(20.dp)).background(Color(0xFFFFE9EC))
                    .clickable(onClick = toQuizzes).padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("♥  Сегодня для нас", color = RefRose, fontSize = 10.sp,
                            fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(7.dp))
                        Text("Скажи партнёру 3 вещи, за которые ты ему благодарен(на).",
                            color = RefInk, fontSize = 14.sp, lineHeight = 17.sp,
                            fontWeight = FontWeight.Bold, maxLines = 2)
                        Spacer(Modifier.height(5.dp))
                        Text("◷  5 минут  ·  Близость", color = RefMuted, fontSize = 8.sp)
                    }
                    Text("💕", fontSize = 36.sp)
                    Spacer(Modifier.width(5.dp))
                    Box(Modifier.size(28.dp).clip(CircleShape).background(RefRose), Alignment.Center) {
                        Text("→", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
            item {
                Row(Modifier.padding(horizontal = 16.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    RefQuickTile(Modifier.weight(1f), Icons.Rounded.Casino, Color(0xFF9B55DE),
                        Color(0xFFF1E7FF), "Случайное\nсвидание", "Пусть любовь\nбудет в деталях", onIdeas)
                    RefQuickTile(Modifier.weight(1f), Icons.Rounded.TrackChanges, Color(0xFF278D86),
                        Color(0xFFE4F5F2), "Наши цели", "${m.days_together} из 32\nвыполнено", onEvents)
                    RefQuickTile(Modifier.weight(1f), Icons.Rounded.EmojiEvents, Color(0xFFD99B20),
                        Color(0xFFFFF4D9), "Достижения", "${m.streak} новых\nнаград", onProfile)
                    RefQuickTile(Modifier.weight(1f), Icons.Rounded.Quiz, Color(0xFF7760D9),
                        Color(0xFFEEE9FF), "Вопросы\nдруг другу", "Узнавайте\nдруг друга глубже", toQuizzes)
                }
            }
            item {
                Column(Modifier.padding(horizontal = 16.dp).fillMaxWidth().clip(RoundedCornerShape(18.dp))
                    .background(Color(0xFFFFFDFC)).padding(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.Image, null, tint = RefMuted, modifier = Modifier.size(17.dp))
                        Spacer(Modifier.width(7.dp))
                        Text("Наши воспоминания", color = RefInk, fontSize = 11.sp,
                            fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                        Text("Все фото  ›", color = RefMuted, fontSize = 8.sp,
                            modifier = Modifier.clickable(onClick = onWidgetSend))
                    }
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        RefMemory(Modifier.weight(1f), partner, "♥  12 янв. 2025", Color(0xFFD28C6F))
                        RefMemory(Modifier.weight(1f), mine, "8 янв. 2025", Color(0xFF8BB5C9))
                        RefMemory(Modifier.weight(1f), partner, "3 янв. 2025", Color(0xFFB26F69))
                        RefMemory(Modifier.weight(1f), mine, "28 дек. 2024", Color(0xFF7AA184))
                    }
                }
            }
            item {
                Row(Modifier.padding(horizontal = 16.dp).fillMaxWidth().height(54.dp)
                    .clip(RoundedCornerShape(15.dp)).background(Brush.horizontalGradient(
                        listOf(Color(0xFFA34579), Color(0xFFD76587))))
                    .clickable(onClick = onIdeas).padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Text("⚄", color = Color.White, fontSize = 25.sp)
                    Spacer(Modifier.width(9.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Чем займёмся сегодня?", color = Color.White, fontSize = 10.sp,
                            fontWeight = FontWeight.Bold)
                        Text("Новый сценарий свидания уже ждёт вас", color = Color.White.copy(alpha = 0.75f),
                            fontSize = 8.sp)
                    }
                    Text("Открыть  →", color = RefRose, fontSize = 9.sp, fontWeight = FontWeight.Bold,
                        modifier = Modifier.clip(RoundedCornerShape(20.dp)).background(Color.White)
                            .padding(horizontal = 12.dp, vertical = 7.dp))
                }
            }
            item {
                Column(Modifier.padding(horizontal = 16.dp).fillMaxWidth().clip(RoundedCornerShape(18.dp))
                    .background(Color(0xFFFFFDFC)).padding(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.CalendarMonth, null, tint = RefMuted, modifier = Modifier.size(17.dp))
                        Spacer(Modifier.width(7.dp))
                        Text("Наши серии", color = RefInk, fontSize = 11.sp, fontWeight = FontWeight.Bold,
                            modifier = Modifier.weight(1f))
                        Text("Все серии  ›", color = RefMuted, fontSize = 8.sp)
                    }
                    Spacer(Modifier.height(7.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        RefStat(Modifier.weight(1f), "♨", "${m.days_together} дней", "Вместе каждый день", RefRose)
                        RefStat(Modifier.weight(1f), "♥", "${m.streak} дней", "Отвечаем на вопросы", RefRose)
                        RefStat(Modifier.weight(1f), "☆", "${if (daily?.my_answer != null) 1 else 0}", "Заданий выполнено", Color(0xFFD69A1B))
                        RefStat(Modifier.weight(1f), "♟", "${m.streak}", "Целей достигнуто", Color(0xFF8B5BC9))
                    }
                }
            }
        }
    }
}
