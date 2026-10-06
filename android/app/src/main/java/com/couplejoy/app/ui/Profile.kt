package com.couplejoy.app.ui

import android.content.Context
import android.content.SharedPreferences
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import com.couplejoy.app.api.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.time.Instant
import java.time.LocalDate
import java.time.Period
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
import kotlin.math.max

/**
 * Данные профиля на этом устройстве.
 * avatar — URL фото на сервере, birth — ГГГГ-ММ-ДД, since — дата начала отношений ГГГГ-ММ-ДД.
 * since в API бэкенда нет, поэтому хранится локально, а «дни вместе» считаются от неё.
 */
data class LocalProfile(
    val avatar: String = "",
    val birth: String = "",
    val since: String = ""
)

object ProfileStore {
    fun load(p: SharedPreferences) = LocalProfile(
        p.getString("my_avatar", "") ?: "",
        p.getString("my_birth", "") ?: "",
        p.getString("since", "") ?: ""
    )

    fun save(p: SharedPreferences, pr: LocalProfile) {
        p.edit()
            .putString("my_avatar", pr.avatar)
            .putString("my_birth", pr.birth)
            .putString("since", pr.since)
            .apply()
    }

    fun clear(p: SharedPreferences) {
        p.edit().remove("my_avatar").remove("my_birth").remove("since").apply()
    }
}

// ---------- даты ----------
private val RU = Locale("ru")
private val FullFmt = DateTimeFormatter.ofPattern("d MMMM yyyy", RU)
private val DayFmt = DateTimeFormatter.ofPattern("d MMMM", RU)

private fun parse(iso: String): LocalDate? = try {
    if (iso.isBlank()) null else LocalDate.parse(iso)
} catch (e: Exception) { null }

fun prettyDate(iso: String): String = parse(iso)?.format(FullFmt) ?: iso
fun prettyDay(iso: String): String = parse(iso)?.format(DayFmt) ?: iso

fun isoToMillis(iso: String): Long? =
    parse(iso)?.atStartOfDay(ZoneOffset.UTC)?.toInstant()?.toEpochMilli()

fun millisToIso(ms: Long): String =
    Instant.ofEpochMilli(ms).atZone(ZoneOffset.UTC).toLocalDate().toString()

fun todayUtcMillis(): Long =
    LocalDate.now().atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli()

/** Сколько дней вместе: считается от даты начала и растёт каждый день. */
fun daysTogether(since: String, fallback: Int): Int {
    val d = parse(since) ?: return fallback
    return max(0L, ChronoUnit.DAYS.between(d, LocalDate.now())).toInt()
}

fun ageOf(birth: String): Int? =
    parse(birth)?.let { Period.between(it, LocalDate.now()).years.takeIf { y -> y in 0..130 } }

fun birthLine(birth: String, ageFallback: Int? = null): String? {
    if (birth.isBlank()) return ageFallback?.let { "$it" }
    val age = ageOf(birth) ?: ageFallback
    return "🎂 " + prettyDay(birth) + (age?.let { " • $it" } ?: "")
}

// ---------- фото ----------
/** Адрес фото: абсолютный URL остаётся как есть, относительный достраивается от base_url. */
fun resolvePhoto(ctx: Context, p: String): String {
    if (p.startsWith("http")) return p
    val base = ctx.getSharedPreferences("cj", Context.MODE_PRIVATE)
        .getString("base_url", ApiClient.DEFAULT_URL)!!.trimEnd('/')
    return base + (if (p.startsWith("/")) p else "/$p")
}

/** Уменьшает фото (до maxSide), учитывает поворот EXIF, сжимает в JPEG. */
private fun compressImage(ctx: Context, uri: Uri, maxSide: Int): ByteArray {
    val cr = ctx.contentResolver
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
    var sample = 1
    while (max(bounds.outWidth, bounds.outHeight) / sample > maxSide * 2) sample *= 2
    val opts = BitmapFactory.Options().apply { inSampleSize = sample }
    val src = cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
        ?: throw IllegalStateException("Не удалось прочитать фото")

    val orientation = try {
        cr.openInputStream(uri)?.use {
            ExifInterface(it).getAttributeInt(
                ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL
            )
        } ?: ExifInterface.ORIENTATION_NORMAL
    } catch (e: Exception) { ExifInterface.ORIENTATION_NORMAL }

    val m = Matrix()
    when (orientation) {
        ExifInterface.ORIENTATION_ROTATE_90 -> m.postRotate(90f)
        ExifInterface.ORIENTATION_ROTATE_180 -> m.postRotate(180f)
        ExifInterface.ORIENTATION_ROTATE_270 -> m.postRotate(270f)
    }
    val scale = maxSide.toFloat() / max(src.width, src.height)
    if (scale < 1f) m.postScale(scale, scale)
    val out: Bitmap = Bitmap.createBitmap(src, 0, 0, src.width, src.height, m, true)

    val bos = ByteArrayOutputStream()
    out.compress(Bitmap.CompressFormat.JPEG, 88, bos)
    return bos.toByteArray()
}

/** Загружает фото на сервер (POST /photos) и возвращает его URL. */
suspend fun uploadImage(ctx: Context, uri: Uri, maxSide: Int = 1024): String =
    withContext(Dispatchers.IO) {
        val bytes = compressImage(ctx, uri, maxSide)
        val part = MultipartBody.Part.createFormData(
            "file", "photo.jpg", bytes.toRequestBody("image/jpeg".toMediaType())
        )
        ApiClient.api.upload(part).url
    }
