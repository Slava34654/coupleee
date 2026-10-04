package com.couplejoy.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** Дополнительные цвета поверх MaterialTheme: фон, градиенты, карточки. */
@Immutable
data class CjExtras(
    val bgTop: Color,
    val bgBottom: Color,
    val accentA: Color,
    val accentB: Color,
    val card: Color,
    val cardBorder: Color,
    val glowA: Color,
    val glowB: Color,
    val good: Color,
    val dark: Boolean
) {
    fun brand(): Brush = Brush.linearGradient(listOf(accentA, accentB))
    fun brandH(): Brush = Brush.horizontalGradient(listOf(accentA, accentB))
}

private val DarkExtras = CjExtras(
    bgTop = Color(0xFF1C1030),
    bgBottom = Color(0xFF0E0817),
    accentA = Color(0xFFFF6B9A),
    accentB = Color(0xFFA77BFF),
    card = Color(0xFF261A3B),
    cardBorder = Color(0x1FFFFFFF),
    glowA = Color(0x55FF6B9A),
    glowB = Color(0x44A77BFF),
    good = Color(0xFF5BE3A8),
    dark = true
)

private val LightExtras = CjExtras(
    bgTop = Color(0xFFFFF0F6),
    bgBottom = Color(0xFFF4EEFF),
    accentA = Color(0xFFF0447D),
    accentB = Color(0xFF8B5CF6),
    card = Color(0xFFFFFFFF),
    cardBorder = Color(0x1A8B5CF6),
    glowA = Color(0x33F0447D),
    glowB = Color(0x338B5CF6),
    good = Color(0xFF12A87A),
    dark = false
)

val LocalCj = staticCompositionLocalOf { DarkExtras }

private val DarkScheme = darkColorScheme(
    primary = Color(0xFFFF6B9A),
    onPrimary = Color.White,
    secondary = Color(0xFFA77BFF),
    onSecondary = Color.White,
    tertiary = Color(0xFFFFB86B),
    background = Color(0xFF0E0817),
    onBackground = Color(0xFFF7EFFF),
    surface = Color(0xFF261A3B),
    onSurface = Color(0xFFF7EFFF),
    surfaceVariant = Color(0xFF30214A),
    onSurfaceVariant = Color(0xFFBCAED6),
    outline = Color(0xFF6E5C8E),
    error = Color(0xFFFF7A8A)
)

private val LightScheme = lightColorScheme(
    primary = Color(0xFFF0447D),
    onPrimary = Color.White,
    secondary = Color(0xFF8B5CF6),
    onSecondary = Color.White,
    tertiary = Color(0xFFFF8F00),
    background = Color(0xFFF4EEFF),
    onBackground = Color(0xFF241339),
    surface = Color.White,
    onSurface = Color(0xFF241339),
    surfaceVariant = Color(0xFFF1E9FF),
    onSurfaceVariant = Color(0xFF6B5A88),
    outline = Color(0xFFB7A6D6),
    error = Color(0xFFD93654)
)

val CjTypography = Typography(
    displaySmall = TextStyle(
        fontWeight = FontWeight.ExtraBold, fontSize = 36.sp,
        lineHeight = 42.sp, letterSpacing = (-0.5).sp
    ),
    headlineMedium = TextStyle(
        fontWeight = FontWeight.Bold, fontSize = 26.sp,
        lineHeight = 32.sp, letterSpacing = (-0.3).sp
    ),
    titleLarge = TextStyle(
        fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 26.sp
    ),
    titleMedium = TextStyle(
        fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp
    ),
    bodyLarge = TextStyle(
        fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp
    ),
    bodyMedium = TextStyle(
        fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp
    ),
    labelLarge = TextStyle(
        fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp
    ),
    labelMedium = TextStyle(
        fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp
    )
)

@Composable
fun AppTheme(dark: Boolean = true, content: @Composable () -> Unit) {
    val extras = if (dark) DarkExtras else LightExtras
    CompositionLocalProvider(LocalCj provides extras) {
        MaterialTheme(
            colorScheme = if (dark) DarkScheme else LightScheme,
            typography = CjTypography,
            content = content
        )
    }
}

fun windowBackgroundColor(dark: Boolean): Int =
    if (dark) 0xFF0E0817.toInt() else 0xFFF4EEFF.toInt()
