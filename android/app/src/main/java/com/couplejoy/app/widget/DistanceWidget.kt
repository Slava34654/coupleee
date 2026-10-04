package com.couplejoy.app.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.ImageProvider
import androidx.glance.action.ActionParameters
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.padding
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.couplejoy.app.MainActivity
import com.couplejoy.app.R
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.location.formatAgo
import com.couplejoy.app.location.formatDistance
import java.util.concurrent.TimeUnit

/**
 * Виджет «Расстояние до партнёра». Только читает /distance с сервера.
 * Свою геопозицию приложение отправляет, пока открыто (см. LocationSync).
 */
class DistanceWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val uid = prefs.getInt("uid", -1)
        var big = "📍"
        var line1 = "Откройте приложение"
        var line2 = ""
        if (uid > 0) {
            try {
                val api = ApiClient.forUrl(prefs.getString("base_url", ApiClient.DEFAULT_URL)!!)
                val d = api.distance(uid)
                val km = d.km
                when {
                    d.partner_name == null -> {
                        line1 = "Ждём партнёра"
                    }
                    !d.sharing -> {
                        line1 = "Включите расстояние"
                        line2 = "Настройки → Расстояние до партнёра"
                    }
                    !d.partner_sharing -> {
                        line1 = "Ждём ${d.partner_name}"
                        line2 = "Он ещё не включил геопозицию"
                    }
                    km != null -> {
                        big = formatDistance(km)
                        line1 = "до ${d.partner_name}"
                        line2 = formatAgo(d.partner_age_min)
                    }
                }
            } catch (e: Exception) {
                line1 = "Нет связи с сервером"
            }
        }
        val white = ColorProvider(Color.White)
        val soft = ColorProvider(Color(0xCCFFFFFF))
        provideContent {
            GlanceTheme {
                Column(
                    modifier = GlanceModifier.fillMaxSize()
                        .background(ImageProvider(R.drawable.widget_distance_bg))
                        .padding(14.dp)
                        .clickable(actionStartActivity<MainActivity>()),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("📍 между вами", style = TextStyle(color = soft, fontSize = 12.sp))
                    Text(
                        big,
                        style = TextStyle(color = white, fontSize = 28.sp, fontWeight = FontWeight.Bold),
                        maxLines = 1
                    )
                    Text(line1, style = TextStyle(color = white, fontSize = 14.sp), maxLines = 1)
                    if (line2.isNotEmpty()) {
                        Text(line2, style = TextStyle(color = soft, fontSize = 11.sp), maxLines = 2)
                    }
                    Text(
                        "🔄",
                        modifier = GlanceModifier.padding(top = 6.dp)
                            .clickable(actionRunCallback<DistanceRefreshAction>())
                    )
                }
            }
        }
    }
}

class DistanceWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = DistanceWidget()
}

class DistanceRefreshAction : ActionCallback {
    override suspend fun onAction(
        context: Context, glanceId: GlanceId, parameters: ActionParameters
    ) {
        WorkManager.getInstance(context)
            .enqueue(OneTimeWorkRequestBuilder<DistanceWidgetWorker>().build())
    }
}

class DistanceWidgetWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        return try {
            val manager = GlanceAppWidgetManager(applicationContext)
            manager.getGlanceIds(DistanceWidget::class.java).forEach { id ->
                DistanceWidget().update(applicationContext, id)
            }
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}

fun scheduleDistanceWidget(ctx: Context) {
    val req = PeriodicWorkRequestBuilder<DistanceWidgetWorker>(15, TimeUnit.MINUTES).build()
    WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
        "cj-distance", ExistingPeriodicWorkPolicy.KEEP, req
    )
}
