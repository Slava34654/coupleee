package com.couplejoy.app.ui

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animate
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Logout
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Casino
import androidx.compose.material.icons.rounded.ChevronRight
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.DarkMode
import androidx.compose.material.icons.rounded.Favorite
import androidx.compose.material.icons.rounded.HourglassTop
import androidx.compose.material.icons.rounded.LightMode
import androidx.compose.material.icons.rounded.PhotoCamera
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Quiz
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Star
import androidx.compose.material.icons.rounded.Style
import androidx.compose.material3.Icon
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.AnswerReq
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.AuthResp
import com.couplejoy.app.api.DailyResp
import com.couplejoy.app.api.EventReq
import com.couplejoy.app.api.EventResp
import com.couplejoy.app.api.Idea
import com.couplejoy.app.api.IdeaReq
import com.couplejoy.app.api.LoginReq
import com.couplejoy.app.api.JournalEntry
import com.couplejoy.app.api.JournalReq
import com.couplejoy.app.api.MeResp
import com.couplejoy.app.api.MoodReq
import com.couplejoy.app.api.DistanceResp
import com.couplejoy.app.api.PackAnsReq
import com.couplejoy.app.api.PackResp
import com.couplejoy.app.api.PackShort
import com.couplejoy.app.api.PairSetupReq
import com.couplejoy.app.api.WidgetResp
import com.couplejoy.app.location.formatAgo
import com.couplejoy.app.location.formatDistance
import com.couplejoy.app.api.RegisterReq
import com.couplejoy.app.api.QuizAnsReq
import com.couplejoy.app.api.QuizResp
import com.couplejoy.app.api.QuizResult
import com.couplejoy.app.api.QuizShort
import com.couplejoy.app.api.TogetherIn
import com.couplejoy.app.api.WidgetPhoto
import com.couplejoy.app.api.WidgetReq
import kotlinx.coroutines.launch

// ---------- общий каркас списка ----------
@Composable
fun ListScreen(content: LazyListScope.() -> Unit) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 12.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = content
    )
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text, style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}

@Composable
private fun ActionTile(
    modifier: Modifier, icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String, sub: String, onClick: () -> Unit
) {
    SoftCard(modifier, onClick = onClick) {
        IconBadge(icon)
        Spacer(Modifier.height(12.dp))
        Text(title, style = MaterialTheme.typography.titleMedium)
        Text(sub, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

// ---------- вход / создание пары ----------
@Composable
fun PairScreen(
    vm: AppVm, initialAccount: AuthResp? = null,
    onDone: (Int, LocalProfile, String) -> Unit
) {
    val x = LocalCj.current
    val ctx = LocalContext.current
    var authMode by remember { mutableStateOf(0) }
    var pairMode by remember { mutableStateOf(0) }
    var account by remember(initialAccount) { mutableStateOf(initialAccount) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordAgain by remember { mutableStateOf("") }
    var name by remember(initialAccount) { mutableStateOf(initialAccount?.name.orEmpty()) }
    var code by remember { mutableStateOf("") }
    var myCode by remember { mutableStateOf<String?>(null) }
    var myProfile by remember { mutableStateOf(LocalProfile()) }
    var birth by remember(initialAccount) { mutableStateOf(initialAccount?.birth.orEmpty()) }
    var since by remember(initialAccount) { mutableStateOf(initialAccount?.together_since.orEmpty()) }
    var avatarUri by remember { mutableStateOf<Uri?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {
        if (it != null) avatarUri = it
    }
    val pulse = rememberInfiniteTransition(label = "logo")
    val ps by pulse.animateFloat(
        1f, 1.08f, infiniteRepeatable(tween(1100), RepeatMode.Reverse), label = "logos"
    )

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Spacer(Modifier.height(12.dp))
        Box(
            Modifier.size(96.dp).graphicsLayer { scaleX = ps; scaleY = ps }
                .clip(RoundedCornerShape(30.dp)).background(x.brand()),
            Alignment.Center
        ) {
            Icon(Icons.Rounded.Favorite, null, tint = Color.White, modifier = Modifier.size(52.dp))
        }
        Text("Enrwine", style = MaterialTheme.typography.displaySmall.copy(brush = x.brand()))
        Text(
            if (account == null) {
                "Сначала войдите или создайте аккаунт. Код подтверждения не нужен."
            } else {
                "Аккаунт готов. Теперь создайте пару или присоединитесь к партнёру."
            },
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(4.dp))
        SoftCard(Modifier.fillMaxWidth()) {
            val currentAccount = account
            if (currentAccount == null) {
                Segmented(listOf("Войти", "Регистрация"), authMode) {
                    authMode = it
                    vm.error = null
                }
                Spacer(Modifier.height(16.dp))
                CjField(
                    email, { email = it }, "Электронная почта",
                    keyboard = KeyboardOptions(keyboardType = KeyboardType.Email)
                )
                Spacer(Modifier.height(12.dp))
                CjField(
                    password, { password = it }, "Пароль",
                    keyboard = KeyboardOptions(keyboardType = KeyboardType.Password),
                    visualTransformation = PasswordVisualTransformation()
                )
                if (authMode == 1) {
                    Spacer(Modifier.height(12.dp))
                    CjField(
                        passwordAgain, { passwordAgain = it }, "Повторите пароль",
                        keyboard = KeyboardOptions(keyboardType = KeyboardType.Password),
                        visualTransformation = PasswordVisualTransformation()
                    )
                }
                Spacer(Modifier.height(16.dp))
                PrimaryButton(
                    if (busy) "Подождите…" else if (authMode == 0) "Войти" else "Зарегистрироваться",
                    {
                        if (authMode == 1 && password != passwordAgain) {
                            vm.error = "Пароли не совпадают"
                        } else {
                            scope.launch {
                                busy = true
                                vm.error = null
                                try {
                                    val r = if (authMode == 0) {
                                        ApiClient.api.login(LoginReq(email.trim(), password))
                                    } else {
                                        ApiClient.api.register(RegisterReq(email.trim(), password))
                                    }
                                    ApiClient.authToken = r.token
                                    if (r.pair_ready) {
                                        onDone(
                                            r.user_id,
                                            LocalProfile(r.avatar, r.birth, r.together_since),
                                            r.token
                                        )
                                    } else {
                                        account = r
                                    }
                                } catch (e: Exception) {
                                    vm.error = if (e is retrofit2.HttpException) {
                                        when (e.code()) {
                                            401 -> "Неверная почта или пароль"
                                            409 -> "Эта почта уже зарегистрирована"
                                            else -> e.message
                                        }
                                    } else e.message
                                }
                                busy = false
                            }
                        }
                    },
                    Modifier.fillMaxWidth(),
                    enabled = email.isNotBlank() && password.length >= 6 &&
                        (authMode == 0 || passwordAgain.isNotBlank()) && !busy
                )
            } else {
                Text("Настройка пары", style = MaterialTheme.typography.titleLarge)
                Spacer(Modifier.height(12.dp))
                Segmented(listOf("Создать пару", "Ввести код"), pairMode) {
                    pairMode = it
                    vm.error = null
                }
                Spacer(Modifier.height(16.dp))
                Box(
                    Modifier.align(Alignment.CenterHorizontally).size(104.dp).clip(CircleShape)
                        .background(x.accentA.copy(alpha = 0.10f), CircleShape)
                        .border(2.dp, x.accentA.copy(alpha = 0.5f), CircleShape)
                        .clickable { pick.launch("image/*") },
                    Alignment.Center
                ) {
                    val u = avatarUri
                    if (u == null) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Rounded.PhotoCamera, null, tint = x.accentA, modifier = Modifier.size(30.dp))
                            Text("Фото", color = x.accentA, style = MaterialTheme.typography.labelMedium)
                        }
                    } else {
                        AsyncImage(u, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                    }
                }
                Spacer(Modifier.height(14.dp))
                CjField(name, { name = it }, "Ваше имя")
                Spacer(Modifier.height(12.dp))
                DateField("Дата рождения (необязательно)", birth, { birth = it })
                Spacer(Modifier.height(12.dp))
                if (pairMode == 0) {
                    DateField("Вместе с…", since, { since = it })
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "После создания получите код, который можно отправить партнёру.",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    CjField(
                        code, { code = it.uppercase() }, "Код партнёра",
                        keyboard = KeyboardOptions(
                            capitalization = androidx.compose.ui.text.input.KeyboardCapitalization.Characters
                        )
                    )
                }
                Spacer(Modifier.height(14.dp))
                PrimaryButton(
                    if (busy) "Сохраняем…" else if (pairMode == 0) "Создать пару" else "Присоединиться",
                    {
                        scope.launch {
                            busy = true
                            vm.error = null
                            try {
                                val av = avatarUri?.let { uploadImage(ctx, it) } ?: currentAccount.avatar
                                val r = ApiClient.api.pairSetup(
                                    PairSetupReq(
                                        currentAccount.user_id, name.trim(), birth, av,
                                        if (pairMode == 0) since else "",
                                        if (pairMode == 1) code else ""
                                    )
                                )
                                val profile = LocalProfile(r.avatar, r.birth, r.together_since)
                                if (pairMode == 0) {
                                    myCode = r.pair_code
                                    myProfile = profile
                                    account = r
                                } else {
                                    onDone(r.user_id, profile, r.token)
                                }
                            } catch (e: Exception) {
                                vm.error = if (e is retrofit2.HttpException && e.code() == 404) {
                                    "Код партнёра не найден"
                                } else e.message
                            }
                            busy = false
                        }
                    },
                    Modifier.fillMaxWidth(),
                    enabled = name.isNotBlank() && (pairMode == 1 || since.isNotBlank()) &&
                        (pairMode == 0 || code.isNotBlank()) && !busy && myCode == null
                )
                myCode?.let { c ->
                    Spacer(Modifier.height(16.dp))
                    Column(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp))
                            .background(x.accentA.copy(alpha = 0.10f))
                            .border(1.dp, x.accentA.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
                            .padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("Код вашей пары", style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(c, fontSize = 34.sp, fontWeight = FontWeight.ExtraBold,
                            letterSpacing = 6.sp, color = x.accentA)
                        Text(
                            "Пара создана. Отправьте этот код партнёру.",
                            textAlign = TextAlign.Center,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(Modifier.height(12.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            GhostButton("Копировать", { clipboard.setText(AnnotatedString(c)) }, Modifier.weight(1f))
                            PrimaryButton(
                                "Продолжить",
                                { onDone(currentAccount.user_id, myProfile, currentAccount.token) },
                                Modifier.weight(1f)
                            )
                        }
                    }
                }
            }
            Err(vm)
        }
    }
}

// ---------- главная ----------
@Composable
private fun HeroPerson(
    name: String, photo: String?, birthText: String?, dim: Boolean, onClick: () -> Unit
) {
    Column(Modifier.width(112.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.clip(CircleShape).clickable(onClick = onClick)) {
            Avatar(name, 72.dp, dim, photo)
        }
        Spacer(Modifier.height(6.dp))
        Text(
            name, color = Color.White, fontWeight = FontWeight.Bold, maxLines = 1,
            style = MaterialTheme.typography.titleMedium
        )
        if (birthText != null) {
            Text(
                birthText, color = Color.White.copy(alpha = 0.85f),
                style = MaterialTheme.typography.labelMedium, maxLines = 1
            )
        }
    }
}

@Composable
private fun HeroDistance(d: DistanceResp?) {
    Column(
        Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            if (d == null) "…" else d.km?.let { formatDistance(it) } ?: "—",
            color = Color.White, fontSize = 52.sp,
            fontWeight = FontWeight.ExtraBold, modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center
        )
        Text(
            "расстояние между вами", color = Color.White.copy(alpha = 0.9f),
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(8.dp))
        Text(
            when {
                d == null -> "Загружаем…"
                d.partner_name == null -> "Появится, когда присоединится партнёр"
                !d.sharing || !d.partner_sharing -> "Включите геопозицию оба: Настройки → Расстояние"
                else -> "обновлено ${formatAgo(d.partner_age_min)}"
            },
            color = Color.White.copy(alpha = 0.8f),
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun HeroPhotos(base: String, w: WidgetResp?) {
    val pics = listOfNotNull(
        w?.partner?.photo?.takeIf { it.isNotBlank() }?.let { base + it },
        w?.mine?.photo?.takeIf { it.isNotBlank() }?.let { base + it }
    )
    if (pics.isEmpty()) {
        Text(
            if (w == null) "Загружаем…" else "Пока нет фото — отправьте первое через «Фото партнёру»",
            color = Color.White.copy(alpha = 0.9f),
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.fillMaxWidth().padding(vertical = 24.dp),
            textAlign = TextAlign.Center
        )
    } else {
        val pager = rememberPagerState(pageCount = { pics.size })
        HorizontalPager(
            state = pager,
            modifier = Modifier.fillMaxWidth().height(240.dp)
                .clip(RoundedCornerShape(20.dp))
        ) { p ->
            AsyncImage(pics[p], null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        }
        Spacer(Modifier.height(8.dp))
        Text(
            "листайте ↔ ${pics.size}",
            color = Color.White.copy(alpha = 0.7f),
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center
        )
    }
}

private val HomeRose = Color(0xFFD94F7B)
private val HomeInk = Color(0xFF552536)
private val HomeMuted = Color(0xFF9A7180)
private val HomeCream = Color(0xFFFFF8F7)

@Composable
private fun HomeSectionTitle(title: String, action: String? = null, onAction: () -> Unit = {}) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(title, color = HomeInk, fontSize = 22.sp, fontWeight = FontWeight.Bold,
            modifier = Modifier.weight(1f))
        if (action != null) {
            Text(action, color = HomeRose, style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.clip(RoundedCornerShape(12.dp)).clickable(onClick = onAction)
                    .padding(horizontal = 6.dp, vertical = 5.dp))
        }
    }
}

@Composable
private fun HomeSpaceTile(
    modifier: Modifier, icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String, subtitle: String, color: Color, onClick: () -> Unit
) {
    val source = remember { MutableInteractionSource() }
    Column(
        modifier.pressScale(source).height(124.dp).clip(RoundedCornerShape(24.dp))
            .background(color).clickable(source, null, onClick = onClick).padding(16.dp),
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        Box(Modifier.size(38.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.72f)),
            contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = HomeInk, modifier = Modifier.size(20.dp))
        }
        Column {
            Text(title, color = HomeInk, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Text(subtitle, color = HomeMuted, style = MaterialTheme.typography.labelMedium,
                maxLines = 1)
        }
    }
}

@Composable
private fun HomeMemory(
    modifier: Modifier, photo: String?, title: String, caption: String?, fallback: Color
) {
    Box(modifier.height(156.dp).clip(RoundedCornerShape(22.dp)).background(fallback)) {
        if (!photo.isNullOrBlank()) {
            AsyncImage(photo, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        } else {
            Box(Modifier.size(120.dp).align(Alignment.TopEnd)
                .background(Brush.radialGradient(listOf(Color.White.copy(alpha = 0.42f), Color.Transparent)), CircleShape))
        }
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(
            listOf(Color.Transparent, Color.Transparent, HomeInk.copy(alpha = 0.88f))
        )))
        Column(Modifier.align(Alignment.BottomStart).padding(14.dp)) {
            Text(title, color = Color.White, fontWeight = FontWeight.Bold, maxLines = 1)
            if (!caption.isNullOrBlank()) {
                Text(caption, color = Color.White.copy(alpha = 0.82f),
                    style = MaterialTheme.typography.labelMedium, maxLines = 1)
            }
        }
    }
}

@Composable
fun LegacyHomeScreen(
    vm: AppVm, profile: LocalProfile,
    toQuizzes: () -> Unit, onWidgetSend: () -> Unit, onProfile: () -> Unit,
    onIdeas: () -> Unit = {}, onEvents: () -> Unit = {}
) {
    val uid = vm.userId ?: return
    val prefs = LocalContext.current.getSharedPreferences("cj", Context.MODE_PRIVATE)
    val base = prefs.getString("base_url", ApiClient.DEFAULT_URL)!!.trimEnd('/')
    var me by remember { mutableStateOf<MeResp?>(null) }
    var dist by remember { mutableStateOf<DistanceResp?>(null) }
    var wphotos by remember { mutableStateOf<WidgetResp?>(null) }
    var daily by remember { mutableStateOf<DailyResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({ loading = it }, { ApiClient.api.me(uid) }) {
        me = it
        vm.io({}, { ApiClient.api.distance(uid) }) { dist = it }
        vm.io({}, { ApiClient.api.widget(uid) }) { wphotos = it }
        vm.io({}, { ApiClient.api.daily(uid) }) { daily = it }
    }
    LaunchedEffect(uid) { reload() }
    val partnerPhoto = wphotos?.partner?.photo?.takeIf { it.isNotBlank() }?.let { base + it }
    val myPhoto = wphotos?.mine?.photo?.takeIf { it.isNotBlank() }?.let { base + it }
    val coverPhoto = partnerPhoto ?: myPhoto
    val hour = remember { java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY) }
    val greeting = when (hour) {
        in 5..11 -> "Доброе утро"
        in 12..17 -> "Добрый день"
        else -> "Добрый вечер"
    }

    LazyColumn(
        Modifier.fillMaxSize().background(HomeCream),
        contentPadding = PaddingValues(start = 18.dp, end = 18.dp, top = 10.dp, bottom = 30.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Row(Modifier.fillMaxWidth().height(52.dp), verticalAlignment = Alignment.CenterVertically) {
                Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(30.dp).clip(CircleShape).background(HomeRose), Alignment.Center) {
                        Icon(Icons.Rounded.Favorite, null, tint = Color.White, modifier = Modifier.size(16.dp))
                    }
                    Spacer(Modifier.width(9.dp))
                    Text("Enrwine", color = HomeInk, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp)
                }
                Box(Modifier.size(42.dp).clip(CircleShape).background(Color(0xFFF4D5DB))
                    .border(2.dp, Color.White, CircleShape).clickable(onClick = onProfile), Alignment.Center) {
                    Avatar(me?.name ?: "E", 42.dp, photo = profile.avatar)
                }
            }
        }
        item { Err(vm) }
        if (loading && me == null) item { HeartLoader() }
        me?.let { m ->
            item {
                Appear(0) {
                    Box(Modifier.fillMaxWidth().height(292.dp).shadow(12.dp, RoundedCornerShape(30.dp))
                        .clip(RoundedCornerShape(30.dp)).background(Brush.linearGradient(
                            listOf(Color(0xFFF2B9A1), Color(0xFFE58A92), Color(0xFF8E4A61))
                        ))) {
                        if (coverPhoto != null) {
                            AsyncImage(coverPhoto, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                        }
                        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(
                            listOf(Color(0x22351620), Color.Transparent, Color(0xD9522437))
                        )))
                        Column(Modifier.align(Alignment.BottomStart).padding(22.dp)) {
                            Text("$greeting, ${m.name}", color = Color.White, fontSize = 27.sp,
                                fontWeight = FontWeight.ExtraBold)
                            Text(
                                m.partner?.let { "Сегодня ещё один день вашей истории" }
                                    ?: "Скоро здесь начнётся ваша общая история",
                                color = Color.White.copy(alpha = 0.9f), style = MaterialTheme.typography.bodyMedium
                            )
                            Spacer(Modifier.height(14.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("♥  ${m.days_together} дней вместе",
                                    Modifier.clip(RoundedCornerShape(50)).background(Color.White.copy(alpha = 0.22f))
                                        .padding(horizontal = 13.dp, vertical = 7.dp),
                                    color = Color.White, style = MaterialTheme.typography.labelLarge)
                                Spacer(Modifier.width(8.dp))
                                Text("🔥 ${m.streak}",
                                    Modifier.clip(RoundedCornerShape(50)).background(Color.White.copy(alpha = 0.22f))
                                        .padding(horizontal = 11.dp, vertical = 7.dp),
                                    color = Color.White, style = MaterialTheme.typography.labelLarge)
                            }
                        }
                    }
                }
            }
            item {
                Appear(1) {
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(Color.White)
                        .border(1.dp, Color(0xFFF2E2E5), RoundedCornerShape(24.dp)).padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("Как твоё настроение?", color = HomeInk, fontWeight = FontWeight.Bold,
                                fontSize = 17.sp)
                            Text("Поделись с любимым человеком", color = HomeMuted,
                                style = MaterialTheme.typography.labelMedium)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            listOf("🥰", "😊", "😌").forEach { emoji ->
                                val selected = m.my_mood?.mood == emoji
                                Box(Modifier.size(38.dp).clip(CircleShape)
                                    .background(if (selected) Color(0xFFFFDCE6) else Color(0xFFFFF3F4))
                                    .border(if (selected) 1.dp else 0.dp, HomeRose, CircleShape)
                                    .clickable {
                                        scope.launch {
                                            try { ApiClient.api.mood(MoodReq(uid, emoji)); reload() }
                                            catch (ex: Exception) { vm.error = ex.message }
                                        }
                                    }, Alignment.Center) { Text(emoji, fontSize = 20.sp) }
                            }
                        }
                    }
                }
            }
            item {
                Appear(2) {
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(26.dp))
                        .background(Brush.horizontalGradient(listOf(Color(0xFF61283D), Color(0xFFD9587D))))
                        .clickable(onClick = toQuizzes).padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("ЗАДАНИЕ ДНЯ", color = Color(0xFFFFCDD9), letterSpacing = 1.2.sp,
                                style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(7.dp))
                            Text(daily?.question?.text ?: "Скажите друг другу, за что вы сегодня благодарны",
                                color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp,
                                maxLines = 3)
                            Spacer(Modifier.height(12.dp))
                            Text("Открыть вопрос  →", color = Color.White,
                                style = MaterialTheme.typography.labelLarge)
                        }
                        Box(Modifier.size(66.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.14f)),
                            Alignment.Center) { Text("💌", fontSize = 32.sp) }
                    }
                }
            }
            item {
                Appear(3) {
                    Column {
                        HomeSectionTitle("Ваши пространства")
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            HomeSpaceTile(Modifier.weight(1f), Icons.Rounded.Casino,
                                "Случайное свидание", "Идея для двоих", Color(0xFFFFE5DE), onIdeas)
                            HomeSpaceTile(Modifier.weight(1f), Icons.Rounded.Star,
                                "Общие цели", "Планы и события", Color(0xFFEAE3F7), onEvents)
                        }
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            HomeSpaceTile(Modifier.weight(1f), Icons.Rounded.Favorite,
                                "Наши моменты", "Фото друг другу", Color(0xFFF9E0E8), onWidgetSend)
                            HomeSpaceTile(Modifier.weight(1f), Icons.Rounded.Quiz,
                                "Вопросы", "Узнать друг друга", Color(0xFFE1EFF1), toQuizzes)
                        }
                    }
                }
            }
            item {
                Appear(4) {
                    Column {
                        HomeSectionTitle("Воспоминания", "Добавить", onWidgetSend)
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            HomeMemory(Modifier.weight(1f), partnerPhoto, "От партнёра",
                                wphotos?.partner?.caption, Color(0xFFD6A69C))
                            HomeMemory(Modifier.weight(1f), myPhoto, "Твоё фото",
                                wphotos?.mine?.caption, Color(0xFFB77786))
                        }
                    }
                }
            }
            item {
                Appear(5) {
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(26.dp))
                        .background(Color(0xFFFFE9EA)).clickable(onClick = onIdeas).padding(20.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(58.dp).clip(RoundedCornerShape(18.dp)).background(Color.White),
                            Alignment.Center) { Text("🌙", fontSize = 29.sp) }
                        Spacer(Modifier.width(15.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Сценарий для свидания", color = HomeInk, fontWeight = FontWeight.Bold,
                                fontSize = 17.sp)
                            Text("Вечер без телефонов, прогулка и любимая музыка",
                                color = HomeMuted, style = MaterialTheme.typography.bodyMedium, maxLines = 2)
                        }
                        Icon(Icons.Rounded.ChevronRight, null, tint = HomeRose)
                    }
                }
            }
            item {
                Appear(6) {
                    Column {
                        HomeSectionTitle("Вы вдвоём")
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                            listOf(
                                Triple("${m.days_together}", "дней вместе", Color(0xFFFFE3E9)),
                                Triple("${m.streak}", "дней серия", Color(0xFFE9E3F4)),
                                Triple(dist?.km?.let { formatDistance(it) } ?: "—", "между вами", Color(0xFFE2EFF0))
                            ).forEach { stat ->
                                Column(Modifier.weight(1f).height(94.dp).clip(RoundedCornerShape(20.dp))
                                    .background(stat.third).padding(12.dp),
                                    verticalArrangement = Arrangement.Center,
                                    horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text(stat.first, color = HomeInk, fontWeight = FontWeight.ExtraBold,
                                        fontSize = if (stat.first.length > 6) 17.sp else 22.sp, maxLines = 1)
                                    Text(stat.second, color = HomeMuted, style = MaterialTheme.typography.labelMedium,
                                        textAlign = TextAlign.Center)
                                }
                            }
                        }
                    }
                }
            }
            item {
                Text("Создавайте вашу историю каждый день  ♥", color = HomeMuted,
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), textAlign = TextAlign.Center)
            }
        }
    }
}

// ---------- профиль ----------
@Composable
fun ProfileScreen(
    vm: AppVm, profile: LocalProfile,
    onSave: (LocalProfile) -> Unit, onBack: (() -> Unit)? = null,
    onEvents: () -> Unit = {},
    onWidget: () -> Unit = {}, onSettings: () -> Unit = {},
    onPremium: () -> Unit = {}
) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var me by remember { mutableStateOf<MeResp?>(null) }
    var busy by remember { mutableStateOf(false) }
    var savingDate by remember { mutableStateOf(false) }
    fun reloadMe() = vm.io({}, { ApiClient.api.me(uid) }) { me = it }
    LaunchedEffect(uid) { reloadMe() }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { u ->
        if (u != null) scope.launch {
            busy = true
            try { onSave(profile.copy(avatar = uploadImage(ctx, u))) }
            catch (e: Exception) { vm.error = e.message }
            busy = false
        }
    }
    val days = me?.days_together ?: 0
    ListScreen {
        item {
            Column {
                ScreenHeader("Профиль", null, onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth(), padding = 22.dp) {
                    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            Modifier.size(128.dp).clip(CircleShape).background(x.brand())
                                .clickable { pick.launch("image/*") },
                            Alignment.Center
                        ) {
                            Avatar(me?.name ?: "?", 128.dp, photo = profile.avatar)
                        }
                        Spacer(Modifier.height(10.dp))
                        Text(me?.name ?: "…", style = MaterialTheme.typography.titleLarge)
                        birthLine(profile.birth)?.let {
                            Text(it, style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Spacer(Modifier.height(12.dp))
                        GhostButton(
                            if (busy) "Загружаем…" else if (profile.avatar.isBlank()) "Добавить фото" else "Сменить фото",
                            { if (!busy) pick.launch("image/*") },
                            icon = Icons.Rounded.PhotoCamera
                        )
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    DateField("Дата рождения", profile.birth, { onSave(profile.copy(birth = it)) })
                    Spacer(Modifier.height(12.dp))
                    DateField(
                        "Вместе с… (общая для пары)",
                        me?.together_since ?: "",
                        {
                            scope.launch {
                                savingDate = true
                                try {
                                    ApiClient.api.together(TogetherIn(uid, it))
                                    reloadMe()
                                } catch (e: Exception) { vm.error = e.message }
                                savingDate = false
                            }
                        }
                    )
                    Spacer(Modifier.height(14.dp))
                    Text(
                        if (savingDate) "Сохраняем…" else "Дней вместе: $days",
                        style = MaterialTheme.typography.titleMedium, color = x.accentA
                    )
                    Spacer(Modifier.height(4.dp))
                }
            }
        }
        item { MenuRow(0, Icons.Rounded.HourglassTop, "Обратный отсчёт", "Годовщины и поездки", onEvents) }
        item { MenuRow(1, Icons.Rounded.PhotoCamera, "Фото на виджет", "Порадуйте партнёра", onWidget) }
        item { MenuRow(2, Icons.Rounded.Star, "Premium", "Подписка через Telegram", onPremium) }
        item { MenuRow(3, Icons.Rounded.Settings, "Настройки", "Тема, сервер, выход", onSettings) }
    }
}

@Composable
private fun MoodBox(label: String, mood: String?, note: String?, modifier: Modifier) {
    Column(
        modifier.clip(RoundedCornerShape(20.dp))
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.06f))
            .padding(vertical = 14.dp, horizontal = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(mood ?: "—", fontSize = 40.sp)
        Text(
            note.orEmpty(), style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center, maxLines = 2
        )
    }
}

@Composable
private fun EmojiButton(e: String, selected: Boolean, onClick: () -> Unit) {
    val x = LocalCj.current
    val s by animateFloatAsState(if (selected) 1.14f else 1f, label = "emo")
    val src = remember { MutableInteractionSource() }
    Box(
        Modifier.size(56.dp).graphicsLayer { scaleX = s; scaleY = s }.pressScale(src, 0.88f)
            .clip(CircleShape)
            .background(if (selected) x.accentA.copy(alpha = 0.25f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.06f), CircleShape)
            .border(if (selected) 2.dp else 0.dp, if (selected) x.accentA else Color.Transparent, CircleShape)
            .clickable(src, null, onClick = onClick),
        Alignment.Center
    ) { Text(e, fontSize = 28.sp) }
}

@Composable
private fun OptionRow(text: String, selected: Boolean, onClick: () -> Unit) {
    val x = LocalCj.current
    val shape = RoundedCornerShape(16.dp)
    val src = remember { MutableInteractionSource() }
    Row(
        Modifier.fillMaxWidth().pressScale(src, 0.98f).clip(shape)
            .background(if (selected) x.accentA.copy(alpha = 0.16f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f), shape)
            .border(1.5.dp, if (selected) x.accentA else Color.Transparent, shape)
            .clickable(src, null, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier.size(20.dp).clip(CircleShape)
                .border(2.dp, if (selected) x.accentA else MaterialTheme.colorScheme.outline, CircleShape),
            Alignment.Center
        ) {
            if (selected) Box(Modifier.size(10.dp).clip(CircleShape).background(x.accentA))
        }
        Spacer(Modifier.width(12.dp))
        Text(text, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
fun QuizScreen(vm: AppVm, id: Int, back: () -> Unit) {
    val uid = vm.userId ?: return
    var q by remember { mutableStateOf<QuizResp?>(null) }
    var res by remember { mutableStateOf<QuizResult?>(null) }
    val scope = rememberCoroutineScope()
    fun reload() {
        vm.io({}, { ApiClient.api.quiz(id, uid) }) { q = it }
        vm.io({}, { ApiClient.api.quizResult(id, uid) }) { res = it }
    }
    LaunchedEffect(id) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader(q?.title ?: "…", "Отвечайте — партнёр ответит отдельно", back)
                Err(vm)
            }
        }
        if (q == null) item { HeartLoader() }
        res?.let {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (it.compatibility != null) {
                                RingProgress(it.compatibility / 100f, "${it.compatibility}%", "совместимость")
                            } else {
                                val f = if (it.total > 0) it.answered_together / it.total.toFloat() else 0f
                                RingProgress(f, "${it.answered_together}/${it.total}", "вместе")
                            }
                            Spacer(Modifier.width(16.dp))
                            Column(Modifier.weight(1f)) {
                                Text(
                                    if (it.compatibility == null) "Ответьте оба — увидите результат"
                                    else "Совместимость: ${it.compatibility}%",
                                    style = MaterialTheme.typography.titleMedium
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "Вместе отвечено: ${it.answered_together}/${it.total}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
        q?.questions?.let { qs ->
            itemsIndexed(qs) { i, qq ->
                Appear(i + 1) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                            Text(
                                "${i + 1}. ${qq.text}", style = MaterialTheme.typography.titleMedium,
                                modifier = Modifier.weight(1f)
                            )
                            if (qq.partner_answered) {
                                Spacer(Modifier.width(8.dp))
                                Text("💜", fontSize = 20.sp)
                            }
                        }
                        Spacer(Modifier.height(10.dp))
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            qq.options.forEachIndexed { oi, opt ->
                                OptionRow(opt, qq.my_option == oi) {
                                    scope.launch {
                                        try {
                                            ApiClient.api.quizAnswer(id, QuizAnsReq(uid, qq.id, oi))
                                            reload()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- темы вопросов ----------
@Composable
fun PackListScreen(vm: AppVm, open: (Int) -> Unit, onBack: () -> Unit, onPremium: () -> Unit) {
    val uid = vm.userId ?: return
    var list by remember { mutableStateOf<List<PackShort>?>(null) }
    LaunchedEffect(uid) { vm.io({}, { ApiClient.api.packs(uid) }) { list = it } }
    val prem = rememberPremium(vm)
    ListScreen {
        item {
            Column {
                ScreenHeader("Темы вопросов", "Ответ партнёра виден, когда ответили оба.", onBack)
                Err(vm)
            }
        }
        if (prem == false) {
            item { PaywallCard("Темы вопросов", onPremium) }
            return@ListScreen
        }
        if (list == null || prem == null) item { HeartLoader() }
        list?.let { l ->
            if (l.isEmpty()) item { EmptyHint("📚", "Пока нет тем") }
            itemsIndexed(l) { i, p ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth(), onClick = { open(p.id) }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(p.title, style = MaterialTheme.typography.titleMedium)
                                if (p.description.isNotBlank()) {
                                    Text(
                                        p.description, style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                            Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Spacer(Modifier.height(12.dp))
                        ProgressBar(if (p.total > 0) p.answered_by_me / p.total.toFloat() else 0f)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Ваших: ${p.answered_by_me}/${p.total} • Вместе: ${p.answered_together}",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun PackScreen(vm: AppVm, id: Int, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    var p by remember { mutableStateOf<PackResp?>(null) }
    var drafts by remember { mutableStateOf<Map<Int, String>>(emptyMap()) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.pack(id, uid) }) { p = it }
    LaunchedEffect(id) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader(p?.title ?: "…", p?.description?.ifBlank { null }, onBack)
                Err(vm)
            }
        }
        if (p == null) item { HeartLoader() }
        p?.questions?.let { qs ->
            itemsIndexed(qs) { i, q ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                            Text(q.text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                            if (q.partner_answered) {
                                Spacer(Modifier.width(8.dp))
                                Text("💜", fontSize = 20.sp)
                            }
                        }
                        Spacer(Modifier.height(12.dp))
                        if (q.my_answer == null) {
                            CjField(
                                drafts[q.id] ?: "", { drafts = drafts + (q.id to it) },
                                "Ваш ответ", singleLine = false, minLines = 2
                            )
                            Spacer(Modifier.height(10.dp))
                            PrimaryButton(
                                "Отправить",
                                {
                                    scope.launch {
                                        try {
                                            ApiClient.api.packAnswer(id, PackAnsReq(uid, q.id, drafts[q.id] ?: ""))
                                            reload()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                },
                                Modifier.fillMaxWidth(), enabled = !(drafts[q.id].isNullOrBlank()),
                                icon = Icons.AutoMirrored.Rounded.Send
                            )
                        } else {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Bubble("Вы", q.my_answer, mine = true)
                                if (q.partner_answer != null) Bubble("Партнёр", q.partner_answer, mine = false)
                                else WaitingBubble("Партнёр ещё отвечает…")
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- вопросы (вопрос дня + викторины) ----------
@Composable
fun QAScreen(vm: AppVm, onPacks: () -> Unit, openQuiz: (Int) -> Unit) {
    val uid = vm.userId ?: return
    var tab by remember { mutableStateOf(0) }
    var d by remember { mutableStateOf<DailyResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    var text by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reloadDaily() = vm.io({ loading = it }, { ApiClient.api.daily(uid) }) { d = it }
    LaunchedEffect(uid) { reloadDaily() }
    var qlist by remember { mutableStateOf<List<QuizShort>?>(null) }
    LaunchedEffect(Unit) {
        vm.io({}, { ApiClient.api.quizzes() }) { qlist = it }
    }
    ListScreen {
        item {
            Column {
                ScreenHeader("Вопросы", "Ежедневный вопрос и викторины")
                Err(vm)
            }
        }
        item {
            Segmented(listOf("Вопрос дня", "Викторины"), tab) { tab = it }
        }
        if (tab == 0) {
            if (loading && d == null) item { HeartLoader() }
            d?.let { dd ->
                item {
                    Appear(0) {
                        SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 22.dp) {
                            Text(
                                "ВОПРОС ДНЯ • ${dd.question.date}",
                                color = Color.White.copy(alpha = 0.85f),
                                style = MaterialTheme.typography.labelMedium
                            )
                            Spacer(Modifier.height(10.dp))
                            Text(
                                dd.question.text, color = Color.White, fontSize = 22.sp,
                                lineHeight = 30.sp, fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
                item {
                    Appear(1) {
                        SoftCard(Modifier.fillMaxWidth()) {
                            if (dd.my_answer == null) {
                                CjField(text, { text = it }, "Ваш ответ", singleLine = false, minLines = 3)
                                Spacer(Modifier.height(12.dp))
                                PrimaryButton(
                                    "Отправить",
                                    {
                                        scope.launch {
                                            try {
                                                ApiClient.api.answer(AnswerReq(uid, text))
                                                text = ""
                                                reloadDaily()
                                            } catch (e: Exception) { vm.error = e.message }
                                        }
                                    },
                                    Modifier.fillMaxWidth(), enabled = text.isNotBlank(),
                                    icon = Icons.AutoMirrored.Rounded.Send
                                )
                            } else {
                                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Bubble("Вы", dd.my_answer, mine = true)
                                    if (dd.partner_answer != null) Bubble("Партнёр", dd.partner_answer, mine = false)
                                    else WaitingBubble("Партнёр ещё отвечает…")
                                }
                            }
                        }
                    }
                }
                item {
                    Appear(2) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            ActionTile(Modifier.weight(1f), Icons.Rounded.Quiz, "Викторины", "Игры для двоих") { tab = 1 }
                            ActionTile(Modifier.weight(1f), Icons.Rounded.Style, "Темы вопросов", "Глубокие разговоры", onPacks)
                        }
                    }
                }
            }
        } else {
            if (qlist == null) item { HeartLoader() }
            qlist?.let { l ->
                if (l.isEmpty()) item { EmptyHint("🎮", "Пока нет викторин") }
                itemsIndexed(l) { i, q ->
                    Appear(i) {
                        SoftCard(Modifier.fillMaxWidth(), onClick = { openQuiz(q.id) }) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                IconBadge(Icons.Rounded.Quiz)
                                Spacer(Modifier.width(14.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(q.title, style = MaterialTheme.typography.titleMedium)
                                    Text(
                                        "Вопросов: ${q.questions}",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                                Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- идеи и журнал ----------
@Composable
fun IdeasScreen(vm: AppVm) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    var tab by remember { mutableStateOf(0) }
    var list by remember { mutableStateOf<List<Idea>?>(null) }
    var lucky by remember { mutableStateOf<Idea?>(null) }
    var title by remember { mutableStateOf("") }
    var filter by remember { mutableStateOf(0) }
    val scope = rememberCoroutineScope()
    fun reloadIdeas() = vm.io({}, { ApiClient.api.ideas() }) { list = it }
    LaunchedEffect(Unit) { reloadIdeas() }
    val shown = list?.filter {
        when (filter) { 1 -> it.done != 1; 2 -> it.done == 1; else -> true }
    }
    var jlist by remember { mutableStateOf<List<JournalEntry>?>(null) }
    var jtitle by remember { mutableStateOf("") }
    var jtext by remember { mutableStateOf("") }
    fun reloadJournal() = vm.io({}, { ApiClient.api.journal(uid) }) { jlist = it }
    LaunchedEffect(uid) { reloadJournal() }
    ListScreen {
        item {
            Column {
                ScreenHeader("Идеи", "Свидания и общие моменты")
                Err(vm)
            }
        }
        item {
            Segmented(listOf("Идеи", "Журнал"), tab) { tab = it }
        }
        if (tab == 0) {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth(), accent = true, padding = 20.dp) {
                        val l = lucky
                        if (l == null) {
                            Text(
                                "Не знаете, куда пойти?", color = Color.White,
                                style = MaterialTheme.typography.titleLarge
                            )
                            Text(
                                "Пусть выберет случай 🎲", color = Color.White.copy(alpha = 0.9f),
                                style = MaterialTheme.typography.bodyMedium
                            )
                        } else {
                            Text(l.title, color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(6.dp))
                            Text(
                                "${l.category} • ${l.budget}", color = Color.White.copy(alpha = 0.9f),
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                        Spacer(Modifier.height(14.dp))
                        Row(
                            Modifier.clip(RoundedCornerShape(16.dp)).background(Color.White)
                                .clickable {
                                    scope.launch {
                                        try { lucky = ApiClient.api.ideaRandom() }
                                        catch (e: Exception) { vm.error = e.message }
                                    }
                                }
                                .padding(horizontal = 18.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Rounded.Casino, null, tint = x.accentA, modifier = Modifier.size(20.dp))
                            Spacer(Modifier.width(8.dp))
                            Text("Мне повезёт", color = x.accentA, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
            item {
                Appear(1) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Text("Своя идея", style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(10.dp))
                        CjField(title, { title = it }, "Что хотите попробовать?")
                        Spacer(Modifier.height(10.dp))
                        PrimaryButton(
                            "Добавить",
                            {
                                scope.launch {
                                    try {
                                        ApiClient.api.ideaAdd(IdeaReq(title))
                                        title = ""
                                        reloadIdeas()
                                    } catch (e: Exception) { vm.error = e.message }
                                }
                            },
                            Modifier.fillMaxWidth(), enabled = title.isNotBlank(), icon = Icons.Rounded.Add
                        )
                    }
                }
            }
            item { Segmented(listOf("Все", "Ждут нас", "Сделано"), filter) { filter = it } }
            if (list == null) item { HeartLoader() }
            shown?.let { s ->
                if (s.isEmpty()) item { EmptyHint("💡", "Здесь пока пусто") }
                itemsIndexed(s) { i, idea ->
                    Appear(i) {
                        SoftCard(Modifier.fillMaxWidth(), padding = 16.dp) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(
                                        idea.title,
                                        style = MaterialTheme.typography.titleMedium.copy(
                                            textDecoration = if (idea.done == 1) TextDecoration.LineThrough else TextDecoration.None
                                        ),
                                        color = if (idea.done == 1) MaterialTheme.colorScheme.onSurfaceVariant
                                        else MaterialTheme.colorScheme.onSurface
                                    )
                                    Spacer(Modifier.height(6.dp))
                                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                        if (idea.category.isNotBlank()) Pill(idea.category, x.accentB)
                                        if (idea.budget.isNotBlank()) Pill(idea.budget, MaterialTheme.colorScheme.tertiary)
                                    }
                                }
                                Spacer(Modifier.width(10.dp))
                                CheckCircle(idea.done == 1) {
                                    scope.launch {
                                        try {
                                            ApiClient.api.ideaDone(idea.id, idea.done != 1)
                                            reloadIdeas()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            item {
                Appear(0) {
                    SoftCard(Modifier.fillMaxWidth()) {
                        Text("Новый момент", style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(10.dp))
                        CjField(jtitle, { jtitle = it }, "Заголовок момента")
                        Spacer(Modifier.height(10.dp))
                        CjField(jtext, { jtext = it }, "Что запомнилось?", singleLine = false, minLines = 3)
                        Spacer(Modifier.height(12.dp))
                        PrimaryButton(
                            "Сохранить момент",
                            {
                                scope.launch {
                                    try {
                                        ApiClient.api.journalAdd(JournalReq(uid, jtitle, jtext))
                                        jtitle = ""; jtext = ""
                                        reloadJournal()
                                    } catch (e: Exception) { vm.error = e.message }
                                }
                            },
                            Modifier.fillMaxWidth(), enabled = jtitle.isNotBlank()
                        )
                    }
                }
            }
            if (jlist == null) item { HeartLoader() }
            jlist?.let { l ->
                if (l.isEmpty()) item { EmptyHint("📖", "Запишите ваш первый общий момент") }
                itemsIndexed(l) { i, j ->
                    Appear(i) {
                        SoftCard(Modifier.fillMaxWidth()) {
                            Row {
                                Box(Modifier.clip(CircleShape).background(LocalCj.current.brand())) {
                                    Avatar(j.author, 40.dp)
                                }
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(j.title, style = MaterialTheme.typography.titleMedium)
                                    if (j.text.isNotBlank()) {
                                        Spacer(Modifier.height(4.dp))
                                        Text(j.text, style = MaterialTheme.typography.bodyLarge)
                                    }
                                    Spacer(Modifier.height(8.dp))
                                    Text(
                                        "${j.author} • ${j.ts}",
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.secondary
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- настройки ----------
@Composable
fun SettingsScreen(
    vm: AppVm, baseUrl: String, dark: Boolean,
    onDark: (Boolean) -> Unit,
    onSaveUrl: (String) -> Unit, onLeavePair: () -> Unit,
    onLogout: () -> Unit, onBack: () -> Unit
) {
    val x = LocalCj.current
    var url by remember(baseUrl) { mutableStateOf(baseUrl) }
    var saved by remember { mutableStateOf(false) }
    ListScreen {
        item {
            Column {
                ScreenHeader("Настройки", null, onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconBadge(if (dark) Icons.Rounded.DarkMode else Icons.Rounded.LightMode)
                        Spacer(Modifier.width(14.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Тёмная тема", style = MaterialTheme.typography.titleMedium)
                            Text(
                                if (dark) "Включена" else "Выключена",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(
                            dark, onDark,
                            colors = SwitchDefaults.colors(
                                checkedTrackColor = x.accentA, checkedThumbColor = Color.White
                            )
                        )
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconBadge(Icons.Rounded.Cloud)
                        Spacer(Modifier.width(14.dp))
                        Text("Адрес сервера", style = MaterialTheme.typography.titleMedium)
                    }
                    Spacer(Modifier.height(10.dp))
                    Text(
                        "По умолчанию: https://ssssw-sladaqqq.amvera.io/  •  ⚠️ Используйте https: обычные http-адреса приложение не примет (защита данных). Для тестов подойдёт эмулятор: http://10.0.2.2:8000/",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(12.dp))
                    CjField(url, { url = it; saved = false }, "http(s)://…")
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        "Сохранить",
                        {
                            onSaveUrl(if (url.endsWith("/")) url else "$url/")
                            saved = true
                        },
                        Modifier.fillMaxWidth()
                    )
                    if (saved) {
                        Spacer(Modifier.height(8.dp))
                        Text("Сохранено ✅", color = x.good, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
        item { Appear(2) { LocationShareCard(vm) } }
        item {
            Appear(3) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Виджет на рабочий стол", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Долгое нажатие по рабочему столу → Виджеты → Enrwine. Обновляется сам каждые 15 минут, показывает дни, настроение и фото партнёра.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
        item {
            Appear(4) {
                GhostButton(
                    "Выйти из пары", onLeavePair,
                    Modifier.fillMaxWidth(), icon = Icons.AutoMirrored.Rounded.Logout
                )
            }
        }
        item {
            Appear(5) {
                GhostButton(
                    "Выйти из аккаунта", onLogout,
                    Modifier.fillMaxWidth(), icon = Icons.AutoMirrored.Rounded.Logout
                )
            }
        }
    }
}

// ---------- фото на виджет ----------
@Composable
fun WidgetSendScreen(vm: AppVm, onBack: () -> Unit, onPremium: () -> Unit) {
    val uid = vm.userId ?: return
    val prem = rememberPremium(vm)
    val x = LocalCj.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var uri by remember { mutableStateOf<Uri?>(null) }
    var caption by remember { mutableStateOf("") }
    var msg by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var mine by remember { mutableStateOf<WidgetPhoto?>(null) }
    var theirs by remember { mutableStateOf<WidgetPhoto?>(null) }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {
        uri = it
    }
    fun reload() = vm.io({}, { ApiClient.api.widget(uid) }) {
        mine = it.mine
        theirs = it.partner
    }
    LaunchedEffect(uid) { reload() }
    val base = ctx.getSharedPreferences("cj", Context.MODE_PRIVATE)
        .getString("base_url", ApiClient.DEFAULT_URL)!!.trimEnd('/')
    ListScreen {
        item {
            Column {
                ScreenHeader("На виджет партнёра", "Фото сразу появится на домашнем экране партнёра.", onBack)
                Err(vm)
            }
        }
        if (prem == false) {
            item { PaywallCard("Фото на виджет", onPremium) }
            return@ListScreen
        }
        if (prem == null) {
            item { HeartLoader() }
            return@ListScreen
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    val shape = RoundedCornerShape(22.dp)
                    Box(
                        Modifier.fillMaxWidth().height(230.dp).clip(shape)
                            .background(x.accentA.copy(alpha = 0.08f), shape)
                            .border(1.5.dp, x.accentA.copy(alpha = 0.4f), shape)
                            .clickable { pick.launch("image/*") },
                        Alignment.Center
                    ) {
                        val u = uri
                        if (u == null) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(Icons.Rounded.PhotoCamera, null, tint = x.accentA, modifier = Modifier.size(40.dp))
                                Spacer(Modifier.height(8.dp))
                                Text("Выбрать фото", color = x.accentA, style = MaterialTheme.typography.titleMedium)
                            }
                        } else {
                            AsyncImage(u, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                        }
                    }
                    if (uri != null) {
                        Spacer(Modifier.height(10.dp))
                        GhostButton("Выбрать другое", { pick.launch("image/*") }, Modifier.fillMaxWidth())
                    }
                    Spacer(Modifier.height(12.dp))
                    CjField(caption, { caption = it }, "Подпись (необязательно)")
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        if (sending) "Отправляем…" else "Отправить на виджет 💞",
                        {
                            scope.launch {
                                sending = true
                                try {
                                    val url = uploadImage(ctx, uri!!)
                                    ApiClient.api.widgetSend(WidgetReq(uid, url, caption))
                                    uri = null
                                    caption = ""
                                    msg = "Отправлено! 💞"
                                    reload()
                                } catch (e: Exception) {
                                    vm.error = e.message
                                }
                                sending = false
                            }
                        },
                        Modifier.fillMaxWidth(), enabled = uri != null && !sending
                    )
                    if (msg.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text(msg, color = x.good, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
        item {
            Appear(1) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Фото партнёра вам", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    val t = theirs
                    if (t != null) {
                        AsyncImage(
                            base + t.photo, null,
                            Modifier.fillMaxWidth().height(240.dp).clip(RoundedCornerShape(20.dp)),
                            contentScale = ContentScale.Crop
                        )
                        if (t.caption.isNotBlank()) {
                            Spacer(Modifier.height(8.dp))
                            Text(t.caption, style = MaterialTheme.typography.bodyLarge)
                        }
                    } else {
                        Text(
                            "Пока ничего нет", style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

// ---------- события ----------
@Composable
fun EventsScreen(vm: AppVm, onBack: () -> Unit) {
    val uid = vm.userId ?: return
    val x = LocalCj.current
    var list by remember { mutableStateOf<List<EventResp>?>(null) }
    var title by remember { mutableStateOf("") }
    var date by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.events(uid) }) { list = it }
    LaunchedEffect(uid) { reload() }
    ListScreen {
        item {
            Column {
                ScreenHeader("Обратный отсчёт", "До самых важных дат", onBack)
                Err(vm)
            }
        }
        item {
            Appear(0) {
                SoftCard(Modifier.fillMaxWidth()) {
                    Text("Новое событие", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    CjField(title, { title = it }, "Событие (годовщина, поездка…)")
                    Spacer(Modifier.height(10.dp))
                    CjField(
                        date, { date = it }, "Дата ГГГГ-ММ-ДД",
                        keyboard = KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                    )
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton(
                        "Добавить",
                        {
                            scope.launch {
                                try {
                                    ApiClient.api.eventAdd(EventReq(uid, title, date))
                                    title = ""; date = ""
                                    reload()
                                } catch (e: Exception) { vm.error = e.message }
                            }
                        },
                        Modifier.fillMaxWidth(), enabled = title.isNotBlank() && date.isNotBlank(),
                        icon = Icons.Rounded.Add
                    )
                }
            }
        }
        if (list == null) item { HeartLoader() }
        list?.let { l ->
            if (l.isEmpty()) item { EmptyHint("⏳", "Добавьте первую важную дату") }
            itemsIndexed(l) { i, e ->
                Appear(i) {
                    SoftCard(Modifier.fillMaxWidth(), padding = 16.dp) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val past = e.days_left < 0
                            Column(
                                Modifier.size(72.dp).clip(RoundedCornerShape(20.dp))
                                    .then(
                                        if (past) Modifier.background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.10f))
                                        else Modifier.background(x.brand())
                                    ),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                Text(
                                    "${if (past) -e.days_left else e.days_left}",
                                    fontSize = 26.sp, fontWeight = FontWeight.ExtraBold,
                                    color = if (past) MaterialTheme.colorScheme.onSurfaceVariant else Color.White
                                )
                                Text(
                                    "дн.", fontSize = 11.sp,
                                    color = if (past) MaterialTheme.colorScheme.onSurfaceVariant else Color.White.copy(alpha = 0.9f)
                                )
                            }
                            Spacer(Modifier.width(14.dp))
                            Column(Modifier.weight(1f)) {
                                Text(e.title, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    if (e.days_left >= 0) "Осталось дней: ${e.days_left}"
                                    else "Было ${-e.days_left} дн. назад",
                                    style = MaterialTheme.typography.bodyMedium
                                )
                                Text(
                                    e.date, style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.secondary
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
