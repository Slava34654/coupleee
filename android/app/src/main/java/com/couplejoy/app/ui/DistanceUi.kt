package com.couplejoy.app.ui

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.LocationOn
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.DistanceResp
import com.couplejoy.app.location.LocationSync
import com.couplejoy.app.location.formatAgo
import com.couplejoy.app.location.formatDistance
import kotlinx.coroutines.launch

/** Карточка в настройках: включить/выключить расстояние до партнёра + текущее значение. */
@Composable
fun LocationShareCard(vm: AppVm) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var on by remember { mutableStateOf(LocationSync.isSharing(ctx)) }
    var busy by remember { mutableStateOf(false) }
    var info by remember { mutableStateOf<DistanceResp?>(null) }

    fun enable() {
        scope.launch {
            busy = true
            try {
                LocationSync.setSharing(ctx, true)
                on = true
                val fail = LocationSync.push(ctx, uid)
                if (fail != null) {
                    vm.error = LocationSync.message(fail)
                }
                info = ApiClient.api.distance(uid)
            } catch (e: Exception) {
                vm.error = e.message
            }
            busy = false
        }
    }

    fun disable() {
        scope.launch {
            busy = true
            try { ApiClient.api.locationStop(uid) } catch (e: Exception) { vm.error = e.message }
            LocationSync.setSharing(ctx, false)
            on = false
            info = null
            LocationSync.refreshDistanceWidget(ctx)
            busy = false
        }
    }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { res ->
        if (res.values.any { it }) enable()
        else vm.error = "Без доступа к геопозиции расстояние посчитать нельзя"
    }

    LaunchedEffect(on) {
        if (on) {
            try { info = ApiClient.api.distance(uid) } catch (e: Exception) { }
        }
    }

    SoftCard(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconBadge(Icons.Rounded.LocationOn)
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text("Расстояние до партнёра", style = MaterialTheme.typography.titleMedium)
                Text(
                    if (on) "Вы делитесь геопозицией" else "Выключено",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Switch(
                checked = on,
                enabled = !busy,
                onCheckedChange = { want ->
                    if (!want) disable()
                    else if (LocationSync.hasPermission(ctx)) enable()
                    else launcher.launch(
                        arrayOf(
                            Manifest.permission.ACCESS_COARSE_LOCATION,
                            Manifest.permission.ACCESS_FINE_LOCATION
                        )
                    )
                },
                colors = SwitchDefaults.colors(
                    checkedTrackColor = x.accentA, checkedThumbColor = Color.White
                )
            )
        }
        val d = info
        if (on && d != null) {
            Spacer(Modifier.height(12.dp))
            val km = d.km
            Text(
                when {
                    km != null -> "Сейчас между вами: ${formatDistance(km)}"
                    d.partner_name == null -> "Появится, когда присоединится партнёр"
                    else -> "Ждём, когда ${d.partner_name} тоже включит геопозицию"
                },
                style = MaterialTheme.typography.titleMedium, color = x.accentA
            )
            if (km != null) {
                Text(
                    "Партнёр: " + formatAgo(d.partner_age_min),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        Text(
            "Партнёр видит только расстояние, но не вашу точку на карте. Работает, когда включили оба. " +
                "Ваше положение обновляется, пока приложение открыто. Выключите переключатель, и данные сотрутся с сервера.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
