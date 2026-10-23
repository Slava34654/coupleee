package com.enrwine.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.MenuBook
import androidx.compose.material.icons.rounded.AutoStories
import androidx.compose.material.icons.rounded.Favorite
import androidx.compose.material.icons.rounded.Image
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.SentimentSatisfied
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.enrwine.app.AppVm
import com.enrwine.app.api.ActivityItem
import com.enrwine.app.api.ActivityResp
import com.enrwine.app.api.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

private data class ActivityStyle(val icon: ImageVector, val color: Color, val title: String)

private fun activityStyle(type: String) = when (type) {
    "mood" -> ActivityStyle(Icons.Rounded.SentimentSatisfied, Color(0xFFE04F78), "Новое настроение")
    "daily" -> ActivityStyle(Icons.Rounded.Notifications, Color(0xFF8C62D6), "Ответ на вопрос дня")
    "pack" -> ActivityStyle(Icons.Rounded.AutoStories, Color(0xFF6D5CC7), "Ответ в наборе вопросов")
    "journal" -> ActivityStyle(Icons.AutoMirrored.Rounded.MenuBook, Color(0xFF2A938B), "Новое воспоминание")
    "tap" -> ActivityStyle(Icons.Rounded.Favorite, Color(0xFFE04F78), "Объятие для тебя")
    else -> ActivityStyle(Icons.Rounded.Image, Color(0xFFD28B22), "Новое фото")
}

private fun activityDetail(item: ActivityItem) = when (item.type) {
    "mood" -> listOf(item.detail, item.extra).filter { it.isNotBlank() }.joinToString("  ")
    "pack" -> item.detail.takeIf { it.isNotBlank() }?.let { "Набор «$it»" }.orEmpty()
    else -> item.detail
}

private fun activityTime(value: String): String = try {
    val time = LocalDateTime.parse(value)
    val day = time.toLocalDate()
    val prefix = when (day) {
        LocalDate.now() -> "Сегодня"
        LocalDate.now().minusDays(1) -> "Вчера"
        else -> day.format(DateTimeFormatter.ofPattern("d MMM"))
    }
    "$prefix, ${time.format(DateTimeFormatter.ofPattern("HH:mm"))}"
} catch (_: Exception) {
    value.replace('T', ' ')
}

@Composable
fun ActivityScreen(vm: AppVm, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    var response by remember { mutableStateOf<ActivityResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    var refresh by remember { mutableStateOf(0) }

    LaunchedEffect(uid, refresh) {
        loading = true
        vm.error = null
        try {
            response = withContext(Dispatchers.IO) { ApiClient.api.activity(uid) }
        } catch (e: Exception) {
            vm.error = e.message
        }
        loading = false
    }

    ListScreen {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.weight(1f)) {
                    ScreenHeader(
                        "Активность партнёра",
                        response?.partner_name?.takeIf { it.isNotBlank() }?.let { "Что нового у $it" },
                        onBack
                    )
                }
                IconCircle(Icons.Rounded.Refresh) { refresh++ }
            }
        }
        item { Err(vm) }
        if (loading) {
            item { HeartLoader() }
        } else if (vm.error == null && response?.items.isNullOrEmpty()) {
            item { EmptyHint("🔔", "Здесь появятся действия партнёра в Enrwine") }
        } else if (response != null) {
            items(response!!.items, key = { it.id }) { activity ->
                ActivityCard(activity)
            }
        }
    }
}

@Composable
private fun ActivityCard(activity: ActivityItem) {
    val context = LocalContext.current
    val style = activityStyle(activity.type)
    val detail = activityDetail(activity)
    SoftCard(Modifier.fillMaxWidth(), padding = 16.dp) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(50.dp).clip(CircleShape).background(style.color.copy(alpha = 0.14f)),
                Alignment.Center
            ) {
                Icon(style.icon, null, tint = style.color, modifier = Modifier.size(27.dp))
            }
            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(style.title, style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold)
                if (detail.isNotBlank()) {
                    Text(detail, style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text(activityTime(activity.ts), style = MaterialTheme.typography.labelMedium,
                    color = style.color)
            }
        }
        if (activity.photo.isNotBlank()) {
            Spacer(Modifier.height(13.dp))
            AsyncImage(
                resolvePhoto(context, activity.photo), null,
                Modifier.fillMaxWidth().height(150.dp).clip(RoundedCornerShape(18.dp)),
                contentScale = ContentScale.Crop
            )
        }
    }
}
