package com.couplejoy.app.widget

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceTheme
import androidx.glance.Image
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
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.padding
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.couplejoy.app.MainActivity
import com.couplejoy.app.api.ApiClient
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

const val PREFS = "cj"
const val PHOTO_FILE = "widget_photo.jpg"

fun downloadBitmap(url: String): Bitmap? {
    return try {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 15000
        c.readTimeout = 15000
        c.connect()
        if (c.responseCode != 200) return null
        BitmapFactory.decodeStream(c.inputStream).also { c.disconnect() }
    } catch (e: Exception) {
        null
    }
}

class CoupleWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val uid = prefs.getInt("uid", -1)
        var title = "💑 CoupleJoy"
        var sub = "Откройте приложение"
        var photoFile: File? = null
        if (uid > 0) {
            try {
                val base = prefs.getString("base_url", ApiClient.DEFAULT_URL)!!
                val api = ApiClient.forUrl(base)
                val me = api.me(uid)
                title = "💞 ${me.days_together} дн. • 🔥 ${me.streak}"
                sub = me.partner?.let { p ->
                    "💜 ${p.name}: ${me.partner_mood?.mood ?: "—"}"
                } ?: "Ждём партнёра…"
                val w = api.widget(uid).partner
                if (w != null) {
                    val bmp = downloadBitmap(base.trimEnd('/') + w.photo)
                    if (bmp != null) {
                        val f = File(context.filesDir, PHOTO_FILE)
                        f.outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 85, it) }
                    }
                }
            } catch (e: Exception) {
                sub = "Нет связи с сервером"
            }
        }
        val cached = File(context.filesDir, PHOTO_FILE)
        if (cached.exists()) photoFile = cached
        val photoBitmap = photoFile?.let {
            try {
                BitmapFactory.decodeFile(it.absolutePath)
            } catch (e: Exception) {
                null
            }
        }
        provideContent {
            GlanceTheme {
                Column(
                    modifier = androidx.glance.GlanceModifier.fillMaxSize()
                        .padding(12.dp)
                        .clickable(actionStartActivity<MainActivity>()),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(title, style = TextStyle(fontSize = 15.sp))
                    if (photoBitmap != null) {
                        Image(ImageProvider(photoBitmap), contentDescription = "Фото",
                            modifier = androidx.glance.GlanceModifier.defaultWeight())
                    } else {
                        Text("📷 фото партнёра появится здесь")
                    }
                    Text(sub)
                    Text("🔄 Обновить",
                        modifier = androidx.glance.GlanceModifier.padding(top = 6.dp)
                            .clickable(actionRunCallback<RefreshAction>()))
                }
            }
        }
    }
}

class WidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = CoupleWidget()
}

class RefreshAction : ActionCallback {
    override suspend fun onAction(
        context: Context, glanceId: GlanceId, parameters: ActionParameters
    ) {
        WorkManager.getInstance(context)
            .enqueue(OneTimeWorkRequestBuilder<WidgetWorker>().build())
    }
}

class WidgetWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        return try {
            val manager = GlanceAppWidgetManager(applicationContext)
            manager.getGlanceIds(CoupleWidget::class.java).forEach { id ->
                CoupleWidget().update(applicationContext, id)
            }
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}

fun scheduleWidget(ctx: Context) {
    val req = PeriodicWorkRequestBuilder<WidgetWorker>(15, TimeUnit.MINUTES).build()
    WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
        "cj-widget", ExistingPeriodicWorkPolicy.KEEP, req
    )
}
