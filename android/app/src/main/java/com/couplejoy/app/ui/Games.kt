package com.couplejoy.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.GameActionReq
import com.couplejoy.app.api.GameStateResp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun GamesScreen(vm: AppVm, onTicTacToe: () -> Unit, onSync: () -> Unit, onIdeas: () -> Unit) {
    LaunchedEffect(Unit) { vm.error = null }
    ListScreen {
        item {
            Text("Игры для пары", style = MaterialTheme.typography.displaySmall)
            Text("Вместе, даже если вы сейчас далеко", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 20.dp) {
                Text("Два телефона · одна игра", color = Color.White, style = MaterialTheme.typography.titleLarge)
                Spacer(Modifier.height(5.dp))
                Text("Откройте одну игру одновременно — ходы появятся у партнёра автоматически.",
                    color = Color.White.copy(.85f))
            }
        }
        item { GameCard("✕ ○", "Крестики-нолики", "Классическая дуэль в реальном времени", "2–5 минут", Color(0xFFC94E72), onTicTacToe) }
        item { GameCard("♡ ?", "Насколько мы синхронны?", "Выберите ответ тайно и сравните совпадение", "6 раундов", Color(0xFF7E8FB2), onSync) }
        item { GameCard("🎲", "Идеи для свиданий", "Случайные и сохранённые планы для двоих", "Без правил", Color(0xFF7FA297), onIdeas) }
    }
}

@Composable
private fun GameCard(icon: String, title: String, subtitle: String, badge: String, tint: Color, onClick: () -> Unit) {
    SoftCard(Modifier.fillMaxWidth(), onClick = onClick, padding = 18.dp) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(64.dp).clip(RoundedCornerShape(20.dp)).background(tint.copy(.13f)), Alignment.Center) {
                Text(icon, color = tint, fontSize = 25.sp, fontWeight = FontWeight.ExtraBold)
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(3.dp))
                Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                Pill(badge, tint)
            }
            Text("›", fontSize = 28.sp, color = tint)
        }
    }
}

@Composable
fun OnlineGameScreen(vm: AppVm, kind: String, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    val scope = rememberCoroutineScope()
    var game by remember { mutableStateOf<GameStateResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    var sending by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var connected by remember { mutableStateOf(true) }
    suspend fun refresh(showLoading: Boolean = false) {
        if (showLoading) loading = true
        try {
            game = ApiClient.api.game(kind, uid)
            error = null
            connected = true
        } catch (e: Exception) {
            connected = false
            if (game == null) error = onlineError(e)
        } finally {
            loading = false
        }
    }
    fun action(name: String, value: Int? = null) {
        if (sending) return
        scope.launch {
            sending = true
            try {
                game = ApiClient.api.gameAction(kind, GameActionReq(uid, name, value))
                error = null
                connected = true
            } catch (e: Exception) {
                error = onlineError(e)
            }
            sending = false
        }
    }
    LaunchedEffect(kind, uid) {
        refresh(true)
        while (true) {
            delay(1500)
            refresh()
        }
    }
    Column(Modifier.fillMaxSize().padding(horizontal = 18.dp, vertical = 10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconCircle(Icons.AutoMirrored.Rounded.ArrowBack, onBack)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(if (kind == "tic_tac_toe") "Крестики-нолики" else "Синхронность",
                    style = MaterialTheme.typography.headlineMedium)
                Text(if (connected) "● онлайн" else "○ переподключаемся…",
                    color = if (connected) Color(0xFF4A9A76) else MaterialTheme.colorScheme.error,
                    fontSize = 12.sp)
            }
        }
        Spacer(Modifier.height(16.dp))
        if (loading && game == null) HeartLoader()
        error?.let {
            Text(it, Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp))
                .background(MaterialTheme.colorScheme.error.copy(.10f))
                .clickable { scope.launch { refresh(true) } }.padding(14.dp),
                color = MaterialTheme.colorScheme.error)
            Spacer(Modifier.height(12.dp))
        }
        game?.let { state ->
            if (state.waiting) WaitingForPartner { scope.launch { refresh(true) } }
            else if (kind == "tic_tac_toe") {
                TicTacToe(state, sending, { action("move", it) }, { action("reset") })
            } else {
                SyncGame(state, sending, { action("choose", it) }, { action("next") }, { action("reset") })
            }
        }
    }
}

private fun onlineError(e: Exception): String = when ((e as? retrofit2.HttpException)?.code()) {
    404 -> "Сервер игр ещё не обновлён. Нажмите, чтобы повторить."
    409 -> "Партнёр уже сделал следующий ход — обновляем игру…"
    503 -> "Сервер временно недоступен. Нажмите, чтобы повторить."
    else -> "Не удалось связаться с игрой. Нажмите, чтобы повторить."
}

@Composable
private fun WaitingForPartner(onRefresh: () -> Unit) {
    SoftCard(Modifier.fillMaxWidth(), padding = 22.dp) {
        Text("💌", fontSize = 44.sp)
        Spacer(Modifier.height(8.dp))
        Text("Ждём партнёра", style = MaterialTheme.typography.titleLarge)
        Text("Когда партнёр присоединится к вашей паре, игра появится здесь автоматически.",
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(16.dp))
        GhostButton("Проверить снова", onRefresh, Modifier.fillMaxWidth())
    }
}

@Composable
private fun TicTacToe(game: GameStateResp, busy: Boolean, onMove: (Int) -> Unit, onReset: () -> Unit) {
    val x = LocalCj.current
    val finished = game.result != "playing"
    val status = when (game.result) {
        "win" -> "Вы победили! ♥"
        "lose" -> "Победил ${game.partner_name}. Реванш?"
        "draw" -> "Ничья — вы идеально равны"
        else -> if (game.my_turn) "Ваш ход · вы играете ${game.my_symbol}" else "Ход ${game.partner_name} · ждём…"
    }
    SoftCard(Modifier.fillMaxWidth(), accent = finished, padding = 18.dp) {
        Text(status, color = if (finished) Color.White else MaterialTheme.colorScheme.onSurface,
            style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth())
    }
    Spacer(Modifier.height(18.dp))
    Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        (0..2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                (0..2).forEach { column ->
                    val index = row * 3 + column
                    val value = game.board.getOrElse(index) { "" }
                    Box(Modifier.weight(1f).aspectRatio(1f).clip(RoundedCornerShape(20.dp))
                        .background(if (value == game.my_symbol) x.accentA.copy(.15f) else x.card)
                        .clickable(enabled = !busy && game.my_turn && !finished && value.isEmpty()) { onMove(index) },
                        Alignment.Center) {
                        Text(value, fontSize = 52.sp, fontWeight = FontWeight.Light,
                            color = if (value == "X") x.accentA else x.accentB)
                    }
                }
            }
        }
    }
    Spacer(Modifier.height(18.dp))
    if (finished) PrimaryButton("Сыграть ещё раз", onReset, Modifier.fillMaxWidth(), enabled = !busy)
}

@Composable
private fun SyncGame(game: GameStateResp, busy: Boolean, onChoose: (Int) -> Unit,
                     onNext: () -> Unit, onReset: () -> Unit) {
    val x = LocalCj.current
    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 18.dp) {
        Text("Раунд ${game.round + 1} · совпадений ${game.score}",
            color = Color.White, style = MaterialTheme.typography.titleLarge)
    }
    Spacer(Modifier.height(14.dp))
    Text(game.prompt, style = MaterialTheme.typography.headlineMedium)
    Spacer(Modifier.height(16.dp))
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        game.options.forEachIndexed { index, option ->
            val mine = game.my_choice == index
            val partner = game.revealed && game.partner_choice == index
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp))
                .background(if (mine) x.accentA.copy(.14f) else x.card)
                .clickable(enabled = !busy && game.my_choice == null && !game.revealed) { onChoose(index) }
                .padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(option, Modifier.weight(1f), fontWeight = if (mine || partner) FontWeight.Bold else FontWeight.Normal)
                if (mine) Pill("Вы", x.accentA)
                if (partner) Pill(game.partner_name ?: "Партнёр", x.accentB)
            }
        }
    }
    AnimatedVisibility(game.my_choice != null && !game.revealed) {
        Text(if (game.partner_chosen) "Сверяем ответы…" else "Партнёр ещё выбирает…",
            Modifier.fillMaxWidth().padding(16.dp), textAlign = TextAlign.Center)
    }
    if (game.revealed) {
        Spacer(Modifier.height(12.dp))
        PrimaryButton("Следующий вопрос", onNext, Modifier.fillMaxWidth(), enabled = !busy)
    }
    TextButton(onClick = onReset, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
        Text("Начать счёт заново", color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
