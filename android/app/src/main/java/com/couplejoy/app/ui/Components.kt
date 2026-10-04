package com.couplejoy.app.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.CalendarMonth
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Favorite
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.SelectableDates
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.couplejoy.app.AppVm
import kotlinx.coroutines.delay

// ---------- нажатия ----------
fun Modifier.pressScale(src: MutableInteractionSource, to: Float = 0.96f): Modifier = composed {
    val pressed by src.collectIsPressedAsState()
    val s by animateFloatAsState(
        if (pressed) to else 1f, spring(0.55f, 450f), label = "press"
    )
    graphicsLayer { scaleX = s; scaleY = s }
}

// ---------- фон с мягким свечением ----------
@Composable
fun Backdrop(content: @Composable BoxScope.() -> Unit) {
    val x = LocalCj.current
    Box(
        Modifier.fillMaxSize()
            .background(Brush.verticalGradient(listOf(x.bgTop, x.bgBottom)))
    ) {
        Box(
            Modifier.size(380.dp).offset((-150).dp, (-130).dp)
                .background(Brush.radialGradient(listOf(x.glowA, Color.Transparent)), CircleShape)
        )
        Box(
            Modifier.size(340.dp).align(Alignment.BottomEnd).offset(130.dp, 110.dp)
                .background(Brush.radialGradient(listOf(x.glowB, Color.Transparent)), CircleShape)
        )
        content()
    }
}

// ---------- плавное появление ----------
@Composable
fun Appear(index: Int = 0, content: @Composable () -> Unit) {
    val a = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        delay(index.coerceAtMost(6) * 60L)
        a.animateTo(1f, tween(450, easing = FastOutSlowInEasing))
    }
    Box(Modifier.graphicsLayer { alpha = a.value; translationY = (1f - a.value) * 40f }) {
        content()
    }
}

// ---------- карточка ----------
@Composable
fun SoftCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    accent: Boolean = false,
    padding: Dp = 18.dp,
    content: @Composable ColumnScope.() -> Unit
) {
    val x = LocalCj.current
    val shape = RoundedCornerShape(26.dp)
    val src = remember { MutableInteractionSource() }
    val base = modifier
        .then(if (onClick != null) Modifier.pressScale(src, 0.97f) else Modifier)
        .shadow(
            if (accent) 14.dp else if (x.dark) 0.dp else 6.dp, shape,
            ambientColor = x.accentB.copy(alpha = 0.25f),
            spotColor = x.accentA.copy(alpha = 0.35f)
        )
        .clip(shape)
        .then(
            if (accent) Modifier.background(x.brand(), shape)
            else Modifier.background(x.card, shape).border(1.dp, x.cardBorder, shape)
        )
        .then(
            if (onClick != null) Modifier.clickable(src, null, onClick = onClick)
            else Modifier
        )
        .padding(padding)
    Column(base, content = content)
}

// ---------- кнопки ----------
@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    icon: ImageVector? = null
) {
    val x = LocalCj.current
    val src = remember { MutableInteractionSource() }
    val shape = RoundedCornerShape(18.dp)
    val fill = if (enabled) Modifier.background(x.brandH(), shape)
    else Modifier.background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.10f), shape)
    Row(
        modifier.heightIn(min = 54.dp).pressScale(src).clip(shape).then(fill)
            .clickable(src, null, enabled = enabled, onClick = onClick)
            .padding(horizontal = 20.dp),
        Arrangement.Center, Alignment.CenterVertically
    ) {
        val c = if (enabled) Color.White else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
        if (icon != null) {
            Icon(icon, null, tint = c, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
        }
        Text(text, color = c, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
    }
}

@Composable
fun GhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null
) {
    val x = LocalCj.current
    val src = remember { MutableInteractionSource() }
    val shape = RoundedCornerShape(18.dp)
    Row(
        modifier.heightIn(min = 54.dp).pressScale(src).clip(shape)
            .background(x.accentA.copy(alpha = 0.10f), shape)
            .border(1.dp, x.accentA.copy(alpha = 0.55f), shape)
            .clickable(src, null, onClick = onClick)
            .padding(horizontal = 20.dp),
        Arrangement.Center, Alignment.CenterVertically
    ) {
        if (icon != null) {
            Icon(icon, null, tint = x.accentA, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
        }
        Text(text, color = x.accentA, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
    }
}

@Composable
fun IconCircle(icon: ImageVector, onClick: () -> Unit) {
    val x = LocalCj.current
    val src = remember { MutableInteractionSource() }
    Box(
        Modifier.size(44.dp).pressScale(src).clip(CircleShape)
            .background(x.card, CircleShape).border(1.dp, x.cardBorder, CircleShape)
            .clickable(src, null, onClick = onClick),
        Alignment.Center
    ) {
        Icon(icon, "Назад", tint = MaterialTheme.colorScheme.onSurface, modifier = Modifier.size(22.dp))
    }
}

@Composable
fun IconBadge(icon: ImageVector, size: Dp = 46.dp) {
    val x = LocalCj.current
    Box(
        Modifier.size(size).clip(RoundedCornerShape(15.dp)).background(x.brand()),
        Alignment.Center
    ) {
        Icon(icon, null, tint = Color.White, modifier = Modifier.size(size * 0.5f))
    }
}

// ---------- поля ----------
@Composable
fun CjField(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier.fillMaxWidth(),
    singleLine: Boolean = true,
    minLines: Int = 1,
    keyboard: KeyboardOptions = KeyboardOptions.Default
) {
    val x = LocalCj.current
    OutlinedTextField(
        value, onChange, modifier,
        label = { Text(label) },
        singleLine = singleLine,
        minLines = if (singleLine) 1 else minLines,
        keyboardOptions = keyboard,
        shape = RoundedCornerShape(18.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = x.accentA,
            unfocusedBorderColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.16f),
            focusedContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
            unfocusedContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
            focusedLabelColor = x.accentA,
            cursorColor = x.accentA
        )
    )
}

// ---------- заголовки ----------
@Composable
fun ScreenHeader(
    title: String,
    subtitle: String? = null,
    onBack: (() -> Unit)? = null
) {
    Row(Modifier.fillMaxWidth().padding(bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        if (onBack != null) {
            IconCircle(Icons.AutoMirrored.Rounded.ArrowBack, onBack)
            Spacer(Modifier.width(12.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.headlineMedium)
            if (subtitle != null) {
                Text(
                    subtitle, style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun Pill(text: String, tint: Color, modifier: Modifier = Modifier) {
    Text(
        text,
        modifier.clip(RoundedCornerShape(50)).background(tint.copy(alpha = 0.16f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
        color = tint, style = MaterialTheme.typography.labelMedium, maxLines = 1
    )
}

@Composable
fun Avatar(letter: String, size: Dp = 52.dp, dim: Boolean = false, photo: String? = null) {
    Box(
        Modifier.size(size).clip(CircleShape)
            .background(
                if (dim) Brush.linearGradient(listOf(Color(0x33FFFFFF), Color(0x22FFFFFF)))
                else Brush.linearGradient(listOf(Color.White.copy(alpha = 0.30f), Color.White.copy(alpha = 0.12f)))
            )
            .border(1.5.dp, Color.White.copy(alpha = 0.5f), CircleShape),
        Alignment.Center
    ) {
        if (!photo.isNullOrBlank()) {
            AsyncImage(
                resolvePhoto(LocalContext.current, photo), null,
                Modifier.fillMaxSize().clip(CircleShape),
                contentScale = ContentScale.Crop
            )
        } else {
            Text(
                letter.take(1).uppercase().ifBlank { "?" },
                color = Color.White, fontSize = (size.value * 0.42f).sp, fontWeight = FontWeight.Bold
            )
        }
    }
}

/** Поле выбора даты через календарь. value — ГГГГ-ММ-ДД или пусто. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DateField(
    label: String,
    value: String,
    onPick: (String) -> Unit,
    modifier: Modifier = Modifier.fillMaxWidth()
) {
    val x = LocalCj.current
    var open by remember { mutableStateOf(false) }
    val shape = RoundedCornerShape(18.dp)
    Row(
        modifier.heightIn(min = 58.dp).clip(shape)
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f), shape)
            .border(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.16f), shape)
            .clickable { open = true }
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                if (value.isBlank()) "Выбрать дату" else prettyDate(value),
                style = MaterialTheme.typography.bodyLarge,
                color = if (value.isBlank()) MaterialTheme.colorScheme.onSurfaceVariant
                else MaterialTheme.colorScheme.onSurface
            )
        }
        Icon(Icons.Rounded.CalendarMonth, null, tint = x.accentA)
    }
    if (open) {
        val limit = todayUtcMillis()
        val state = rememberDatePickerState(
            initialSelectedDateMillis = isoToMillis(value),
            yearRange = 1930..java.time.LocalDate.now().year,
            selectableDates = object : SelectableDates {
                override fun isSelectableDate(utcTimeMillis: Long): Boolean = utcTimeMillis <= limit
            }
        )
        DatePickerDialog(
            onDismissRequest = { open = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { onPick(millisToIso(it)) }
                    open = false
                }) { Text("Готово", color = x.accentA) }
            },
            dismissButton = {
                TextButton(onClick = { open = false }) { Text("Отмена", color = x.accentA) }
            }
        ) { DatePicker(state) }
    }
}

/** Переключатель сегментов (вкладки внутри экрана). */
@Composable
fun Segmented(options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    val x = LocalCj.current
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp))
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.07f))
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        options.forEachIndexed { i, t ->
            val sel = i == selected
            val bg by animateColorAsState(if (sel) x.accentA else Color.Transparent, label = "seg")
            Box(
                Modifier.weight(1f).clip(RoundedCornerShape(14.dp)).background(bg)
                    .clickable { onSelect(i) }.padding(vertical = 10.dp),
                Alignment.Center
            ) {
                Text(
                    t, fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
                    color = if (sel) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center, maxLines = 1
                )
            }
        }
    }
}

@Composable
fun CheckCircle(checked: Boolean, onClick: () -> Unit) {
    val x = LocalCj.current
    val bg by animateColorAsState(if (checked) x.good else Color.Transparent, label = "chk")
    val src = remember { MutableInteractionSource() }
    Box(
        Modifier.size(32.dp).pressScale(src, 0.85f).clip(CircleShape).background(bg)
            .border(2.dp, if (checked) x.good else MaterialTheme.colorScheme.outline, CircleShape)
            .clickable(src, null, onClick = onClick),
        Alignment.Center
    ) {
        if (checked) Icon(Icons.Rounded.Check, null, tint = Color.White, modifier = Modifier.size(18.dp))
    }
}

@Composable
fun ProgressBar(fraction: Float, modifier: Modifier = Modifier) {
    val x = LocalCj.current
    val f by animateFloatAsState(fraction.coerceIn(0f, 1f), tween(700), label = "pb")
    Box(
        modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(50))
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.10f))
    ) {
        Box(
            Modifier.fillMaxWidth(f).height(8.dp).clip(RoundedCornerShape(50))
                .background(x.brandH())
        )
    }
}

/** Пузырь ответа. mine = ваш (справа, цветной), иначе партнёра (слева). */
@Composable
fun Bubble(label: String, text: String, mine: Boolean) {
    val x = LocalCj.current
    val shape = RoundedCornerShape(
        topStart = 22.dp, topEnd = 22.dp,
        bottomStart = if (mine) 22.dp else 6.dp,
        bottomEnd = if (mine) 6.dp else 22.dp
    )
    Column(
        Modifier.fillMaxWidth(),
        horizontalAlignment = if (mine) Alignment.End else Alignment.Start
    ) {
        Text(
            label, style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
        Text(
            text,
            Modifier.fillMaxWidth(0.88f).clip(shape)
                .then(
                    if (mine) Modifier.background(x.brand(), shape)
                    else Modifier.background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f), shape)
                )
                .padding(horizontal = 16.dp, vertical = 12.dp),
            color = if (mine) Color.White else MaterialTheme.colorScheme.onSurface,
            style = MaterialTheme.typography.bodyLarge
        )
    }
}

@Composable
fun WaitingBubble(text: String) {
    val t = rememberInfiniteTransition(label = "wait")
    val a by t.animateFloat(
        0.45f, 1f, infiniteRepeatable(tween(900), RepeatMode.Reverse), label = "waita"
    )
    Text(
        text,
        Modifier.graphicsLayer { alpha = a }
            .clip(RoundedCornerShape(20.dp))
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.06f))
            .padding(horizontal = 16.dp, vertical = 10.dp),
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        style = MaterialTheme.typography.bodyMedium
    )
}

// ---------- загрузка / пустота / ошибка ----------
@Composable
fun HeartLoader() {
    val x = LocalCj.current
    val t = rememberInfiniteTransition(label = "hb")
    val s by t.animateFloat(
        0.82f, 1.18f, infiniteRepeatable(tween(650), RepeatMode.Reverse), label = "hbs"
    )
    Box(Modifier.fillMaxWidth().padding(36.dp), Alignment.Center) {
        Icon(
            Icons.Rounded.Favorite, null, tint = x.accentA,
            modifier = Modifier.size(44.dp).graphicsLayer { scaleX = s; scaleY = s }
        )
    }
}

@Composable
fun EmptyHint(emoji: String, text: String) {
    Column(
        Modifier.fillMaxWidth().padding(vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(emoji, fontSize = 44.sp)
        Spacer(Modifier.height(8.dp))
        Text(
            text, color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium
        )
    }
}

@Composable
fun Err(vm: AppVm) {
    val e = vm.error ?: return
    val c = MaterialTheme.colorScheme.error
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp)
            .clip(RoundedCornerShape(16.dp)).background(c.copy(alpha = 0.14f))
            .border(1.dp, c.copy(alpha = 0.4f), RoundedCornerShape(16.dp))
            .clickable { vm.error = null }
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("Ошибка: $e", color = c, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        Text("✕", color = c)
    }
}

// ---------- кольцо совместимости ----------
@Composable
fun RingProgress(fraction: Float, center: String, sub: String) {
    val x = LocalCj.current
    val f by animateFloatAsState(fraction.coerceIn(0f, 1f), tween(1000, easing = FastOutSlowInEasing), label = "ring")
    val track = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.10f)
    Box(Modifier.size(132.dp), Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val w = 12.dp.toPx()
            val tl = Offset(w / 2, w / 2)
            val sz = Size(size.width - w, size.height - w)
            drawArc(track, -90f, 360f, false, tl, sz, style = Stroke(w, cap = StrokeCap.Round))
            drawArc(
                Brush.sweepGradient(listOf(x.accentB, x.accentA, x.accentB)),
                -90f, 360f * f, false, tl, sz, style = Stroke(w, cap = StrokeCap.Round)
            )
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(center, fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text(sub, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
