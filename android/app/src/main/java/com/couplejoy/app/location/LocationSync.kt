package com.couplejoy.app.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat
import androidx.core.os.CancellationSignal
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.LocationReq
import com.couplejoy.app.widget.DistanceWidgetWorker
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

const val PREF_SHARE_LOC = "share_loc"

/** Определение геопозиции и отправка её на сервер. Работает только пока приложение открыто. */
object LocationSync {

    fun hasPermission(ctx: Context): Boolean =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED

    fun isSharing(ctx: Context): Boolean =
        ctx.getSharedPreferences("cj", Context.MODE_PRIVATE)
            .getBoolean(PREF_SHARE_LOC, false) && hasPermission(ctx)

    fun setSharing(ctx: Context, on: Boolean) {
        ctx.getSharedPreferences("cj", Context.MODE_PRIVATE)
            .edit().putBoolean(PREF_SHARE_LOC, on).apply()
    }

    /** Свежая точка: берём недавнюю известную (до 10 мин) или запрашиваем новую (до 10 с). */
    @SuppressLint("MissingPermission")
    suspend fun currentLocation(ctx: Context): Location? {
        if (!hasPermission(ctx)) return null
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val providers = try {
            lm.getProviders(true).filter { it != LocationManager.PASSIVE_PROVIDER }
        } catch (e: Exception) { emptyList() }
        val last = providers
            .mapNotNull { runCatching { lm.getLastKnownLocation(it) }.getOrNull() }
            .maxByOrNull { it.time }
        if (last != null && System.currentTimeMillis() - last.time < 10 * 60_000L) return last
        val provider = providers.firstOrNull { it == LocationManager.NETWORK_PROVIDER }
            ?: providers.firstOrNull()
            ?: return last
        val fresh = withTimeoutOrNull(10_000L) {
            suspendCancellableCoroutine<Location?> { cont ->
                val signal = CancellationSignal()
                cont.invokeOnCancellation { signal.cancel() }
                try {
                    LocationManagerCompat.getCurrentLocation(
                        lm, provider, signal, ContextCompat.getMainExecutor(ctx)
                    ) { loc -> if (cont.isActive) cont.resume(loc) }
                } catch (e: Exception) {
                    if (cont.isActive) cont.resume(null)
                }
            }
        }
        return fresh ?: last
    }

    /** Отправляет свою точку на сервер. true — получилось. */
    suspend fun push(ctx: Context, uid: Int): Boolean {
        val loc = currentLocation(ctx) ?: return false
        ApiClient.api.locationSend(LocationReq(uid, loc.latitude, loc.longitude))
        refreshDistanceWidget(ctx)
        return true
    }

    fun refreshDistanceWidget(ctx: Context) {
        WorkManager.getInstance(ctx)
            .enqueue(OneTimeWorkRequestBuilder<DistanceWidgetWorker>().build())
    }
}

/** 0.4 → «Меньше 1 км», 7.46 → «7,5 км», 633.2 → «633 км», 12345 → «12 345 км». */
fun formatDistance(km: Double): String = when {
    km < 1.0 -> "Меньше 1 км"
    km < 10.0 -> String.format(java.util.Locale("ru"), "%.1f км", km)
    else -> String.format(java.util.Locale("ru"), "%,d км", Math.round(km))
}

fun formatAgo(min: Int?): String = when {
    min == null -> ""
    min < 1 -> "обновлено только что"
    min < 60 -> "обновлено $min мин назад"
    min < 24 * 60 -> "обновлено ${min / 60} ч назад"
    else -> "обновлено ${min / (24 * 60)} дн. назад"
}
