package com.enrwine.app.widget

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.action.ActionParameters
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.ContentScale
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.padding
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.enrwine.app.MainActivity
import com.enrwine.app.R
import com.enrwine.app.api.Api
import com.enrwine.app.api.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

const val PREFS = "enrwine"
private const val PHOTO_PREFIX = "widget_photo_"

internal data class WidgetSession(val uid: Int, val api: Api, val baseUrl: String)

internal fun widgetSession(context: Context): WidgetSession? {
    val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    val uid = prefs.getInt("uid", -1)
    val token = prefs.getString("token", "").orEmpty()
    if (uid <= 0 || token.isBlank()) return null
    val base = prefs.getString("base_url", ApiClient.DEFAULT_URL) ?: ApiClient.DEFAULT_URL
    ApiClient.authToken = token
    return WidgetSession(uid, ApiClient.forUrl(base), base.trimEnd('/'))
}

private fun photoCache(context: Context, uid: Int) =
    File(context.noBackupFilesDir, "$PHOTO_PREFIX$uid.jpg")

fun clearWidgetPhotoCache(context: Context) {
    context.noBackupFilesDir.listFiles { file -> file.name.startsWith(PHOTO_PREFIX) }
        ?.forEach { it.delete() }
}

private fun photoUrl(base: String, value: String): String = when {
    value.startsWith("http://") || value.startsWith("https://") -> value
    value.startsWith("/") -> base + value
    else -> "$base/$value"
}

private suspend fun downloadBitmap(url: String): Bitmap? = withContext(Dispatchers.IO) {
    var connection: HttpURLConnection? = null
    try {
        connection = URL(url).openConnection() as HttpURLConnection
        connection.connectTimeout = 10_000
        connection.readTimeout = 10_000
        connection.connect()
        if (connection.responseCode != HttpURLConnection.HTTP_OK) return@withContext null
        if (connection.contentLengthLong > 8 * 1024 * 1024) return@withContext null
        val bytes = connection.inputStream.use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(16 * 1024)
            var total = 0
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                total += count
                if (total > 8 * 1024 * 1024) return@withContext null
                output.write(buffer, 0, count)
            }
            output.toByteArray()
        }
        val source = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return@withContext null
        val maxSide = 1000
        if (source.width <= maxSide && source.height <= maxSide) source else {
            val scale = maxSide.toFloat() / maxOf(source.width, source.height)
            Bitmap.createScaledBitmap(source, (source.width * scale).toInt(),
                (source.height * scale).toInt(), true).also { source.recycle() }
        }
    } catch (_: Exception) {
        null
    } finally {
        connection?.disconnect()
    }
}

class EnrwineWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val session = widgetSession(context)
        var title = "Enrwine • для двоих"
        var partnerLine = "Откройте приложение, чтобы войти"
        var caption = ""
        var photoBitmap: Bitmap? = null

        if (session != null) {
            val cache = photoCache(context, session.uid)
            try {
                val me = session.api.me(session.uid)
                title = "${me.days_together} дней вместе  •  ${me.streak} серия"
                partnerLine = me.partner?.let { partner ->
                    "${partner.name}  ${me.partner_mood?.mood ?: "♡"}"
                } ?: "Пригласите партнёра в пару"
                val photo = session.api.widget(session.uid).partner
                caption = photo?.caption.orEmpty()
                if (photo?.photo.isNullOrBlank()) {
                    withContext(Dispatchers.IO) { cache.delete() }
                } else {
                    val fresh = downloadBitmap(photoUrl(session.baseUrl, photo!!.photo))
                    if (fresh != null) {
                        withContext(Dispatchers.IO) {
                            val temp = File(cache.parentFile, "${cache.name}.tmp")
                            temp.outputStream().use { fresh.compress(Bitmap.CompressFormat.JPEG, 88, it) }
                            if (!temp.renameTo(cache)) {
                                temp.copyTo(cache, overwrite = true)
                                temp.delete()
                            }
                        }
                        fresh.recycle()
                    }
                }
            } catch (_: Exception) {
                partnerLine = "Нет связи • показаны последние данные"
            }
            photoBitmap = withContext(Dispatchers.IO) {
                if (cache.exists()) BitmapFactory.decodeFile(cache.absolutePath) else null
            }
        }

        val white = ColorProvider(Color.White)
        val soft = ColorProvider(Color(0xE6FFFFFF))
        val muted = ColorProvider(Color(0xBFFFFFFF))
        provideContent {
            GlanceTheme {
                Column(
                    modifier = GlanceModifier.fillMaxSize()
                        .background(ImageProvider(R.drawable.widget_enrwine_bg))
                        .padding(14.dp)
                        .clickable(actionStartActivity(Intent(context, MainActivity::class.java))),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text("ENRWINE  ♡", style = TextStyle(color = muted, fontSize = 11.sp,
                        fontWeight = FontWeight.Bold))
                    Text(title, style = TextStyle(color = white, fontSize = 16.sp,
                        fontWeight = FontWeight.Bold), maxLines = 1)
                    if (photoBitmap != null) {
                        Image(
                            ImageProvider(photoBitmap), "Фото от партнёра",
                            modifier = GlanceModifier.fillMaxWidth().defaultWeight()
                                .padding(top = 8.dp, bottom = 8.dp).cornerRadius(18.dp),
                            contentScale = ContentScale.Crop
                        )
                    } else {
                        Column(
                            modifier = GlanceModifier.fillMaxWidth().defaultWeight()
                                .padding(vertical = 12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("💌", style = TextStyle(fontSize = 30.sp))
                            Text("Здесь появится фото партнёра",
                                style = TextStyle(color = soft, fontSize = 12.sp))
                        }
                    }
                    if (caption.isNotBlank()) {
                        Text("“$caption”", style = TextStyle(color = soft, fontSize = 12.sp), maxLines = 1)
                    }
                    Text(partnerLine, style = TextStyle(color = white, fontSize = 13.sp,
                        fontWeight = FontWeight.Bold), maxLines = 1)
                    Text("Обновить  ↻", style = TextStyle(color = soft, fontSize = 11.sp),
                        modifier = GlanceModifier.padding(top = 5.dp)
                            .clickable(actionRunCallback<RefreshAction>()))
                }
            }
        }
    }
}

class WidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = EnrwineWidget()
    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        scheduleWidget(context)
    }
    override fun onDisabled(context: Context) {
        super.onDisabled(context)
        WorkManager.getInstance(context).cancelUniqueWork("enrwine-widget")
    }
}

class RefreshAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        refreshAllWidgets(context)
    }
}

class WidgetWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = try {
        val manager = GlanceAppWidgetManager(applicationContext)
        manager.getGlanceIds(EnrwineWidget::class.java).forEach {
            EnrwineWidget().update(applicationContext, it)
        }
        Result.success()
    } catch (_: Exception) {
        Result.retry()
    }
}

private val networkConstraint = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.CONNECTED).build()

fun refreshAllWidgets(context: Context) {
    val work = WorkManager.getInstance(context)
    work.enqueueUniqueWork("enrwine-widget-now", ExistingWorkPolicy.REPLACE,
        OneTimeWorkRequestBuilder<WidgetWorker>().setConstraints(networkConstraint).build())
    work.enqueueUniqueWork("enrwine-distance-now", ExistingWorkPolicy.REPLACE,
        OneTimeWorkRequestBuilder<DistanceWidgetWorker>().setConstraints(networkConstraint).build())
}

fun scheduleWidget(context: Context) {
    val request = PeriodicWorkRequestBuilder<WidgetWorker>(15, TimeUnit.MINUTES)
        .setConstraints(networkConstraint).build()
    WorkManager.getInstance(context).enqueueUniquePeriodicWork(
        "enrwine-widget", ExistingPeriodicWorkPolicy.KEEP, request
    )
}
