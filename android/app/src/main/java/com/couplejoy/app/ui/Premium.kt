package com.couplejoy.app.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.LinkCodeIn
import com.couplejoy.app.api.PremiumOut
import kotlinx.coroutines.launch

const val BOT_LINK = "https://t.me/Enrwine_bot"
const val PREMIUM_PRICE = "99 ⭐ / 30 дней"

/** null — грузится, true/false — есть ли подписка. */
@Composable
fun rememberPremium(vm: AppVm): Boolean? {
    val uid = vm.userId ?: return false
    var p by remember { mutableStateOf<Boolean?>(null) }
    LaunchedEffect(uid) {
        vm.io({}, { ApiClient.api.premium(uid).premium }) { p = it }
    }
    return p
}

@Composable
fun PaywallCard(what: String, onOpen: () -> Unit) {
    Appear(0) {
        SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
            Text("💫 Это Premium", color = Color.White,
                style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(8.dp))
            Text(
                "$what — по подписке ($PREMIUM_PRICE) через Telegram-бота. " +
                    "Оплата звёздами, продление одной кнопкой.",
                color = Color.White.copy(alpha = 0.92f),
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(Modifier.height(14.dp))
            GhostButton("Открыть Premium", onOpen, Modifier.fillMaxWidth())
        }
    }
}

@Composable
fun PremiumScreen(vm: AppVm, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf<PremiumOut?>(null) }
    var code by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    fun reload() = vm.io({}, { ApiClient.api.premium(uid) }) { status = it }
    LaunchedEffect(uid) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader("Premium 💫", "Подписка через Telegram-бота", onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
                    val st = status
                    if (st == null) {
                        Text("Проверяем подписку…", color = Color.White,
                            style = MaterialTheme.typography.bodyLarge)
                    } else if (st.premium) {
                        Text("Premium активен ✅", color = Color.White,
                            fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(6.dp))
                        Text("Действует до ${st.until}", color = Color.White.copy(alpha = 0.9f),
                            style = MaterialTheme.typography.bodyLarge)
                    } else {
                        Text("Premium не активен", color = Color.White,
                            fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(6.dp))
                        Text("Все функции за $PREMIUM_PRICE", color = Color.White.copy(alpha = 0.9f),
                            style = MaterialTheme.typography.bodyLarge)
                    }
                    Spacer(Modifier.height(12.dp))
                    GhostButton("Обновить статус", { reload() }, Modifier.fillMaxWidth())
                }
            }
        }
        item {
            Appear(2) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Пригласить друга 💌", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Друг ставит приложение и покупает Premium — тебе +7 дней бесплатно за каждого.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        "Пригласить друга",
                        {
                            ctx.startActivity(
                                Intent(
                                    Intent.ACTION_VIEW,
                                    Uri.parse("$BOT_LINK?start=ref_$uid")
                                )
                            )
                        },
                        Modifier.fillMaxWidth()
                    )
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Привязка Telegram", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "1. Нажми «Показать код»\n2. Открой бота кнопкой ниже — код подставится сам\n3. Нажми в боте «Купить Premium 💫» и оплати звёздами",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(12.dp))
                    val c = code
                    if (c == null) {
                        PrimaryButton(
                            if (busy) "…" else "Показать код",
                            {
                                scope.launch {
                                    busy = true
                                    try {
                                        code = ApiClient.api.premiumCode(LinkCodeIn(uid)).code
                                    } catch (e: Exception) { vm.error = e.message }
                                    busy = false
                                }
                            },
                            Modifier.fillMaxWidth(), enabled = !busy
                        )
                    } else {
                        Text(
                            c, fontSize = 34.sp, fontWeight = FontWeight.ExtraBold,
                            letterSpacing = 6.sp, color = LocalCj.current.accentA
                        )
                        Spacer(Modifier.height(12.dp))
                        PrimaryButton(
                            "Открыть бота",
                            {
                                ctx.startActivity(
                                    Intent(Intent.ACTION_VIEW, Uri.parse("$BOT_LINK?start=$c"))
                                )
                            },
                            Modifier.fillMaxWidth()
                        )
                    }
                }
            }
        }
    }
}
