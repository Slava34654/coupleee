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
import androidx.compose.material.icons.rounded.AutoStories
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Lightbulb
import androidx.compose.material.icons.rounded.MoreHoriz
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
import com.couplejoy.app.ui.AppTheme
import com.couplejoy.app.ui.Backdrop
import com.couplejoy.app.ui.DailyScreen
import com.couplejoy.app.ui.EventsScreen
import com.couplejoy.app.ui.HomeScreen
import com.couplejoy.app.ui.IdeasScreen
import com.couplejoy.app.ui.JournalScreen
import com.couplejoy.app.ui.LocalCj
import com.couplejoy.app.ui.MoreScreen
import com.couplejoy.app.ui.PackListScreen
import com.couplejoy.app.ui.PackScreen
import com.couplejoy.app.ui.PairScreen
import com.couplejoy.app.ui.QuizListScreen
import com.couplejoy.app.ui.QuizScreen
import com.couplejoy.app.ui.SettingsScreen
import com.couplejoy.app.ui.WidgetSendScreen
import com.couplejoy.app.ui.windowBackgroundColor
import com.couplejoy.app.widget.WidgetWorker
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
                error = (e.message ?: "network error")
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
        scheduleWidget(this)
        if (vm.userId == null) {
            vm.userId = prefs.getInt("uid", -1).takeIf { it >= 0 }
        }
        setContent { CoupleApp(this, vm, prefs) }
    }
}

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val Tabs = listOf(
    Tab("home", "Главная", Icons.Rounded.Home),
    Tab("daily", "Вопрос", Icons.Rounded.QuestionAnswer),
    Tab("ideas", "Идеи", Icons.Rounded.Lightbulb),
    Tab("journal", "Журнал", Icons.Rounded.AutoStories),
    Tab("more", "Ещё", Icons.Rounded.MoreHoriz)
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

    fun refreshWidget() {
        WorkManager.getInstance(ctx).enqueue(OneTimeWorkRequestBuilder<WidgetWorker>().build())
    }

    AppTheme(dark) {
        val nav = rememberNavController()
        val entry by nav.currentBackStackEntryAsState()
        val route = entry?.destination?.route
        val showBar = route != null && Tabs.any { it.route == route }

        fun goTab(r: String) = nav.navigate(r) {
            popUpTo("home") { saveState = true }
            launchSingleTop = true
            restoreState = true
        }

        Backdrop {
            Scaffold(
                containerColor = Color.Transparent,
                bottomBar = { if (showBar) BottomBar(route) { goTab(it) } }
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
                        PairScreen(vm) { uid ->
                            prefs.edit().putInt("uid", uid).apply()
                            vm.userId = uid
                            vm.error = null
                            refreshWidget()
                            nav.navigate("home") { popUpTo("pair") { inclusive = true } }
                        }
                    }
                    composable("home") {
                        HomeScreen(vm, { nav.navigate("quizzes") }, { nav.navigate("widget") })
                    }
                    composable("daily") {
                        DailyScreen(vm, { nav.navigate("quizzes") }, { nav.navigate("packs") })
                    }
                    composable("ideas") { IdeasScreen(vm) }
                    composable("journal") { JournalScreen(vm) }
                    composable("more") {
                        MoreScreen(
                            onQuizzes = { nav.navigate("quizzes") },
                            onPacks = { nav.navigate("packs") },
                            onEvents = { nav.navigate("events") },
                            onWidget = { nav.navigate("widget") },
                            onSettings = { nav.navigate("settings") }
                        )
                    }
                    composable("quizzes") {
                        QuizListScreen(vm, { nav.navigate("quiz/$it") }, { nav.popBackStack() })
                    }
                    composable(
                        "quiz/{id}",
                        arguments = listOf(navArgument("id") { type = NavType.IntType })
                    ) { e ->
                        QuizScreen(vm, e.arguments?.getInt("id") ?: 0) { nav.popBackStack() }
                    }
                    composable("packs") {
                        PackListScreen(vm, { nav.navigate("pack/$it") }, { nav.popBackStack() })
                    }
                    composable(
                        "pack/{id}",
                        arguments = listOf(navArgument("id") { type = NavType.IntType })
                    ) { e ->
                        PackScreen(vm, e.arguments?.getInt("id") ?: 0) { nav.popBackStack() }
                    }
                    composable("events") { EventsScreen(vm) { nav.popBackStack() } }
                    composable("widget") { WidgetSendScreen(vm) { nav.popBackStack() } }
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
                            onLogout = {
                                prefs.edit().putInt("uid", -1).apply()
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
