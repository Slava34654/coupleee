package com.couplejoy.app

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.QuestionAnswer
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.ui.AppTheme
import com.couplejoy.app.ui.DailyScreen
import com.couplejoy.app.ui.EventsScreen
import com.couplejoy.app.ui.HomeScreen
import com.couplejoy.app.ui.IdeasScreen
import com.couplejoy.app.ui.JournalScreen
import com.couplejoy.app.ui.PackListScreen
import com.couplejoy.app.ui.PackScreen
import com.couplejoy.app.ui.PairScreen
import com.couplejoy.app.ui.QuizListScreen
import com.couplejoy.app.ui.QuizScreen
import com.couplejoy.app.ui.SettingsScreen
import com.couplejoy.app.ui.WidgetSendScreen
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

data class Tab(val route: String, val label: String, val icon: ImageVector)

val TABS = listOf(
    Tab("home", "Главная", Icons.Filled.Favorite),
    Tab("daily", "Вопрос", Icons.Filled.QuestionAnswer),
    Tab("ideas", "Идеи", Icons.Filled.Lightbulb),
    Tab("journal", "Журнал", Icons.Filled.MenuBook),
    Tab("events", "События", Icons.Filled.DateRange),
    Tab("settings", "Настройки", Icons.Filled.Settings),
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("cj", Context.MODE_PRIVATE)
        ApiClient.init(prefs.getString("base_url", ApiClient.DEFAULT_URL)!!)
        scheduleWidget(this)
        setContent {
            AppTheme {
                val vm: AppVm = viewModel()
                if (vm.userId == null) {
                    val saved = prefs.getInt("uid", -1)
                    if (saved > 0) vm.userId = saved
                }
                var baseUrl by androidx.compose.runtime.remember {
                    androidx.compose.runtime.mutableStateOf(
                        prefs.getString("base_url", ApiClient.DEFAULT_URL)!!)
                }
                val nav = rememberNavController()
                val start = if (vm.userId == null) "pair" else "home"
                val entry by nav.currentBackStackEntryAsState()
                val route = entry?.destination?.route
                Scaffold(
                    bottomBar = {
                        if (vm.userId != null && TABS.any { it.route == route }) {
                            NavigationBar {
                                TABS.forEach { t ->
                                    NavigationBarItem(
                                        selected = route == t.route,
                                        onClick = { nav.navigate(t.route) },
                                        icon = { Icon(t.icon, t.label) },
                                        label = { Text(t.label) }
                                    )
                                }
                            }
                        }
                    }
                ) { pad ->
                    NavHost(nav, startDestination = start,
                            modifier = Modifier.padding(pad)) {
                        composable("pair") {
                            PairScreen(vm) { uid ->
                                prefs.edit().putInt("uid", uid).apply()
                                vm.userId = uid
                                nav.navigate("home") { popUpTo("pair") { inclusive = true } }
                            }
                        }
                        composable("home") {
                            HomeScreen(vm, { nav.navigate("quizlist") },
                                { nav.navigate("wsend") })
                        }
                        composable("wsend") { WidgetSendScreen(vm) }
                        composable("settings") {
                            SettingsScreen(vm, baseUrl,
                                onSaveUrl = {
                                    prefs.edit().putString("base_url", it).apply()
                                    baseUrl = it
                                    ApiClient.init(it)
                                },
                                onLogout = {
                                    prefs.edit().remove("uid").apply()
                                    vm.userId = null
                                    while (nav.popBackStack()) {
                                    }
                                    nav.navigate("pair")
                                })
                        }
                        composable("daily") { DailyScreen(vm, { nav.navigate("quizlist") }, { nav.navigate("packs") }) }
                        composable("packs") { PackListScreen(vm) { nav.navigate("pack/$it") } }
                        composable("pack/{id}",
                            arguments = listOf(navArgument("id") { type = NavType.IntType })
                        ) { e -> PackScreen(vm, e.arguments!!.getInt("id")) }
                        composable("quizlist") { QuizListScreen(vm) { nav.navigate("quiz/$it") } }
                        composable("quiz/{id}",
                            arguments = listOf(navArgument("id") { type = NavType.IntType })
                        ) { e -> QuizScreen(vm, e.arguments!!.getInt("id")) { nav.popBackStack() } }
                        composable("ideas") { IdeasScreen(vm) }
                        composable("journal") { JournalScreen(vm) }
                        composable("events") { EventsScreen(vm) }
                    }
                }
            }
        }
    }
}
