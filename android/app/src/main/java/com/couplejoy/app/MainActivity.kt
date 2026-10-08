package com.couplejoy.app

import android.content.Context
import android.content.SharedPreferences
import android.graphics.Color as AColor
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Favorite
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Lightbulb
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.QuestionAnswer
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.background
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.AuthResp
import com.couplejoy.app.ui.AppTheme
import com.couplejoy.app.ui.Backdrop
import com.couplejoy.app.ui.EventsScreen
import com.couplejoy.app.ui.HomeScreen
import com.couplejoy.app.ui.GamesScreen
import com.couplejoy.app.ui.OnlineGameScreen
import com.couplejoy.app.ui.IdeasScreen
import com.couplejoy.app.ui.LocalCj
import com.couplejoy.app.ui.LocalProfile
import com.couplejoy.app.ui.ProfileScreen
import com.couplejoy.app.ui.ProfileStore
import com.couplejoy.app.ui.PackListScreen
import com.couplejoy.app.ui.QAScreen
import com.couplejoy.app.ui.PackScreen
import com.couplejoy.app.ui.PetGameScreen
import com.couplejoy.app.ui.PremiumScreen
import com.couplejoy.app.ui.PairScreen
import com.couplejoy.app.ui.QuizScreen
import com.couplejoy.app.ui.SettingsScreen
import com.couplejoy.app.ui.WidgetSendScreen
import com.couplejoy.app.ui.windowBackgroundColor
import com.couplejoy.app.widget.WidgetWorker
import com.couplejoy.app.location.LocationSync
import com.couplejoy.app.widget.scheduleDistanceWidget
import com.couplejoy.app.widget.scheduleWidget
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AppVm : ViewModel() {
    var userId by mutableStateOf<Int?>(null)
    var error by mutableStateOf<String?>(null)

    fun <T> io(setLoading: (Boolean) -> Unit = {}, block: suspend () -> T,
               onOk: (T) -> Unit) {
        viewModelScope.launch {
            setLoading(true)
            error = null
            try {
                val r = withContext(Dispatchers.IO) { block() }
                onOk(r)
            } catch (e: Exception) {
                error = if (e is retrofit2.HttpException && e.code() == 401) {
                    "Сессия недействительна — выйдите и войдите заново (Настройки → Выйти)"
                } else {
                    (e.message ?: "network error")
                }
            }
            setLoading(false)
        }
    }
}

class MainActivity : ComponentActivity() {
    private val vm: AppVm by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("cj", Context.MODE_PRIVATE)
        ApiClient.init(prefs.getString("base_url", ApiClient.DEFAULT_URL)!!)
        ApiClient.authToken = prefs.getString("token", "") ?: ""
        scheduleWidget(this)
        scheduleDistanceWidget(this)
        if (vm.userId == null && ApiClient.authToken.isNotBlank()) {
            vm.userId = prefs.getInt("uid", -1).takeIf { it >= 0 }
        }
        setContent { CoupleApp(this, vm, prefs) }
    }
}

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val Tabs = listOf(
    Tab("home", "Главная", Icons.Rounded.Home),
    Tab("pet", "Питомец", Icons.Rounded.Favorite),
    Tab("qa", "Вопросы", Icons.Rounded.QuestionAnswer),
    Tab("ideas", "Идеи", Icons.Rounded.Lightbulb),
    Tab("profile", "Профиль", Icons.Rounded.Person)
)

@Composable
private fun BottomBar(current: String?, onSelect: (String) -> Unit) {
    val x = LocalCj.current
    val shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
    Box(
        Modifier.shadow(18.dp, shape, ambientColor = x.accentB, spotColor = x.accentA)
            .clip(shape).background(x.card)
    ) {
        NavigationBar(containerColor = Color.Transparent, tonalElevation = 0.dp) {
            Tabs.forEach { t ->
                NavigationBarItem(
                    selected = current == t.route,
                    onClick = { onSelect(t.route) },
                    icon = { Icon(t.icon, t.label) },
                    label = { Text(t.label) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = x.accentA,
                        selectedTextColor = x.accentA,
                        indicatorColor = x.accentA.copy(alpha = 0.16f),
                        unselectedIconColor = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant,
                        unselectedTextColor = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant
                    )
                )
            }
        }
    }
}

@Composable
fun CoupleApp(activity: ComponentActivity, vm: AppVm, prefs: SharedPreferences) {
    val ctx = LocalContext.current
    var dark by remember { mutableStateOf(prefs.getBoolean("dark", true)) }
    var profile by remember { mutableStateOf(ProfileStore.load(prefs)) }
    var pairingAccount by remember { mutableStateOf<AuthResp?>(null) }
    var baseUrl by remember {
        mutableStateOf(prefs.getString("base_url", ApiClient.DEFAULT_URL)!!)
    }

    // системные панели и фон окна под тему
    DisposableEffect(dark) {
        val style = if (dark) SystemBarStyle.dark(AColor.TRANSPARENT)
        else SystemBarStyle.light(AColor.TRANSPARENT, AColor.TRANSPARENT)
        activity.enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
        activity.window.setBackgroundDrawable(ColorDrawable(windowBackgroundColor(dark)))
        onDispose { }
    }

    // Пока приложение открыто — отправляем свою геопозицию (если пользователь включил «Расстояние»)
    DisposableEffect(vm.userId) {
        val uid = vm.userId
        val obs = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME &&
                uid != null && LocationSync.isSharing(ctx)
            ) {
                vm.viewModelScope.launch {
                    try { LocationSync.push(ctx, uid) } catch (e: Exception) { }
                }
            }
        }
        activity.lifecycle.addObserver(obs)
        onDispose { activity.lifecycle.removeObserver(obs) }
    }

    fun refreshWidget() {
        WorkManager.getInstance(ctx).enqueue(OneTimeWorkRequestBuilder<WidgetWorker>().build())
    }

    AppTheme(dark) {
        val nav = rememberNavController()
        val entry by nav.currentBackStackEntryAsState()
        val route = entry?.destination?.route
        val selectedTab = if (route == "games") "pet" else route
        val showBar = route == "games" || (route != null && Tabs.any { it.route == route })

        fun goTab(r: String) = nav.navigate(r) {
            popUpTo("home") { saveState = true }
            launchSingleTop = true
            restoreState = true
        }

        Backdrop {
            Scaffold(
                containerColor = Color.Transparent,
                bottomBar = { if (showBar) BottomBar(selectedTab) { goTab(it) } }
            ) { pad ->
                NavHost(
                    nav,
                    startDestination = if (vm.userId != null) "home" else "pair",
                    modifier = Modifier.padding(pad).consumeWindowInsets(pad).imePadding(),
                    enterTransition = { fadeIn(tween(240)) + slideInVertically(tween(280)) { it / 24 } },
                    exitTransition = { fadeOut(tween(120)) },
                    popEnterTransition = { fadeIn(tween(240)) },
                    popExitTransition = { fadeOut(tween(120)) + androidx.compose.animation.slideOutVertically(tween(200)) { it / 24 } }
                ) {
                    composable("pair") {
                        PairScreen(vm, pairingAccount) { uid, pr, tok ->
                            ProfileStore.save(prefs, pr)
                            profile = pr
                            pairingAccount = null
                            prefs.edit().putInt("uid", uid).putString("token", tok).apply()
                            ApiClient.authToken = tok
                            vm.userId = uid
                            vm.error = null
                            refreshWidget()
                            nav.navigate("home") { popUpTo("pair") { inclusive = true } }
                        }
                    }
                    composable("home") {
                        HomeScreen(
                            vm, profile,
                            { goTab("qa") }, { nav.navigate("widget") },
                            { goTab("profile") }, { goTab("ideas") },
                            { nav.navigate("events") }
                        )
                    }
                    composable("pet") {
                        PetGameScreen(vm, onGames = { nav.navigate("games") })
                    }
                    composable("games") {
                        GamesScreen(
                            vm,
                            { nav.navigate("game/tic_tac_toe") },
                            { nav.navigate("game/sync") },
                            { goTab("ideas") }
                        )
                    }
                    composable(
                        "game/{kind}",
                        arguments = listOf(navArgument("kind") { type = NavType.StringType })
                    ) { e ->
                        OnlineGameScreen(
                            vm,
                            e.arguments?.getString("kind") ?: "tic_tac_toe"
                        ) { nav.popBackStack() }
                    }
                    composable("qa") {
                        QAScreen(vm, { nav.navigate("packs") }, { nav.navigate("quiz/$it") })
                    }
                    composable("ideas") {
                        IdeasScreen(vm)
                    }
                    composable(
                        "quiz/{id}",
                        arguments = listOf(navArgument("id") { type = NavType.IntType })
                    ) { e ->
                        QuizScreen(vm, e.arguments?.getInt("id") ?: 0) { nav.popBackStack() }
                    }
                    composable("packs") {
                        PackListScreen(
                            vm, { nav.navigate("pack/$it") }, { nav.popBackStack() },
                            { nav.navigate("premium") }
                        )
                    }
                    composable("premium") {
                        PremiumScreen(vm) { nav.popBackStack() }
                    }
                    composable("profile") {
                        ProfileScreen(
                            vm, profile,
                            onSave = {
                                profile = it
                                ProfileStore.save(prefs, it)
                            },
                            onEvents = { nav.navigate("events") },
                            onWidget = { nav.navigate("widget") },
                            onSettings = { nav.navigate("settings") },
                            onPremium = { nav.navigate("premium") }
                        )
                    }
                    composable(
                        "pack/{id}",
                        arguments = listOf(navArgument("id") { type = NavType.IntType })
                    ) { e ->
                        PackScreen(vm, e.arguments?.getInt("id") ?: 0) { nav.popBackStack() }
                    }
                    composable("events") { EventsScreen(vm) { nav.popBackStack() } }
                    composable("widget") {
                        WidgetSendScreen(vm, { nav.popBackStack() }, { nav.navigate("premium") })
                    }
                    composable("settings") {
                        SettingsScreen(
                            vm = vm, baseUrl = baseUrl, dark = dark,
                            onDark = {
                                dark = it
                                prefs.edit().putBoolean("dark", it).apply()
                            },
                            onSaveUrl = {
                                baseUrl = it
                                prefs.edit().putString("base_url", it).apply()
                                ApiClient.init(it)
                            },
                            onLeavePair = {
                                val leaving = vm.userId
                                if (leaving != null) vm.viewModelScope.launch {
                                    vm.error = null
                                    try {
                                        val account = withContext(Dispatchers.IO) {
                                            ApiClient.api.pairLeave(leaving)
                                        }
                                        val pr = LocalProfile(
                                            account.avatar, account.birth, account.together_since
                                        )
                                        ProfileStore.save(prefs, pr)
                                        profile = pr
                                        pairingAccount = account
                                        LocationSync.setSharing(ctx, false)
                                        refreshWidget()
                                        nav.navigate("pair") {
                                            popUpTo(nav.graph.id) { inclusive = true }
                                        }
                                    } catch (e: Exception) {
                                        vm.error = e.message
                                    }
                                }
                            },
                            onLogout = {
                                val leaving = vm.userId
                                if (leaving != null && LocationSync.isSharing(ctx)) {
                                    vm.viewModelScope.launch {
                                        try { ApiClient.api.locationStop(leaving) } catch (e: Exception) { }
                                    }
                                }
                                LocationSync.setSharing(ctx, false)
                                prefs.edit().putInt("uid", -1).remove("token").apply()
                                ApiClient.authToken = ""
                                ProfileStore.clear(prefs)
                                profile = LocalProfile()
                                pairingAccount = null
                                vm.userId = null
                                vm.error = null
                                refreshWidget()
                                nav.navigate("pair") { popUpTo(nav.graph.id) { inclusive = true } }
                            },
                            onBack = { nav.popBackStack() }
                        )
                    }
                }
            }
        }
    }
}
