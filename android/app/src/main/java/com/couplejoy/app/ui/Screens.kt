package com.couplejoy.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.couplejoy.app.AppVm
import com.couplejoy.app.api.AnswerReq
import com.couplejoy.app.api.ApiClient
import com.couplejoy.app.api.DailyResp
import com.couplejoy.app.api.EventReq
import com.couplejoy.app.api.EventResp
import com.couplejoy.app.api.Idea
import com.couplejoy.app.api.IdeaReq
import com.couplejoy.app.api.JoinReq
import com.couplejoy.app.api.JournalEntry
import com.couplejoy.app.api.JournalReq
import com.couplejoy.app.api.MeResp
import com.couplejoy.app.api.MoodReq
import com.couplejoy.app.api.PackAnsReq
import com.couplejoy.app.api.PackResp
import com.couplejoy.app.api.PackShort
import com.couplejoy.app.api.PairReq
import com.couplejoy.app.api.QuizAnsReq
import com.couplejoy.app.api.QuizResp
import com.couplejoy.app.api.QuizResult
import com.couplejoy.app.api.QuizShort
import kotlinx.coroutines.launch

@Composable
fun Err(vm: AppVm) {
    vm.error?.let { Text("Ошибка: $it", color = MaterialTheme.colorScheme.error) }
}

// ---------- вход / создание пары ----------
@Composable
fun PairScreen(vm: AppVm, onDone: (Int) -> Unit) {
    var name by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var myCode by remember { mutableStateOf<String?>(null) }
    var myUid by remember { mutableStateOf<Int?>(null) }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(24.dp), Arrangement.spacedBy(12.dp)) {
        Text("💑 CoupleJoy", fontSize = 30.sp, fontWeight = FontWeight.Bold)
        Text("Пространство для двоих: настроение, вопросы, свидания, журнал.")
        Err(vm)
        OutlinedTextField(name, { name = it }, Modifier.fillMaxWidth(),
            label = { Text("Ваше имя") })
        Button({
            scope.launch {
                try {
                    val r = ApiClient.api.pair(PairReq(name))
                    myCode = r.pair_code
                    myUid = r.user_id
                } catch (e: Exception) { vm.error = e.message }
            }
        }, enabled = name.isNotBlank()) { Text("Создать пару") }
        myCode?.let {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), Arrangement.spacedBy(8.dp)) {
                    Text("Код вашей пары:", fontWeight = FontWeight.Bold)
                    Text(it, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                    Text("Партнёр введёт его у себя. Вы уже внутри:")
                    Button({ myUid?.let(onDone) }) { Text("Войти") }
                }
            }
        }
        OutlinedTextField(code, { code = it.uppercase() },
            Modifier.fillMaxWidth(), label = { Text("Код партнёра") })
        Button({
            scope.launch {
                try {
                    onDone(ApiClient.api.join(JoinReq(name, code)).user_id)
                } catch (e: Exception) { vm.error = e.message }
            }
        }, enabled = name.isNotBlank() && code.isNotBlank()) { Text("Присоединиться") }
    }
}

// ---------- главная ----------
@Composable
fun HomeScreen(vm: AppVm, toQuizzes: () -> Unit) {
    val uid = vm.userId ?: return
    var me by remember { mutableStateOf<MeResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({ loading = it }, { ApiClient.api.me(uid) }) { me = it }
    LaunchedEffect(uid) { reload() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("💑 Главная", fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Err(vm)
            if (loading && me == null) CircularProgressIndicator()
        }
        me?.let { m ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), Arrangement.spacedBy(4.dp)) {
                        Text("Вместе уже ${m.days_together} дн. 🔥 Серия: ${m.streak}",
                            fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text("Вы: ${m.name}" +
                            (m.partner?.let { "  •  Партнёр: ${it.name}" } ?: "  •  ждём партнёра…"))
                    }
                }
            }
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), Arrangement.spacedBy(8.dp)) {
                        Text("Настроение", fontWeight = FontWeight.Bold)
                        Text("Вы: ${m.my_mood?.mood ?: "—"} ${m.my_mood?.note ?: ""}")
                        Text("Партнёр: ${m.partner_mood?.mood ?: "—"} ${m.partner_mood?.note ?: ""}")
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("😍", "🥰", "😊", "😢", "😡").forEach { e ->
                                OutlinedButton({
                                    scope.launch {
                                        try {
                                            ApiClient.api.mood(MoodReq(uid, e))
                                            reload()
                                        } catch (ex: Exception) { vm.error = ex.message }
                                    }
                                }) { Text(e, fontSize = 18.sp) }
                            }
                        }
                    }
                }
            }
            item {
                OutlinedButton(toQuizzes, Modifier.fillMaxWidth()) {
                    Text("🎮 Викторины и совместимость")
                }
            }
        }
    }
}

// ---------- ежедневный вопрос ----------
@Composable
fun DailyScreen(vm: AppVm, toQuizzes: () -> Unit, onPacks: () -> Unit) {
    val uid = vm.userId ?: return
    var d by remember { mutableStateOf<DailyResp?>(null) }
    var loading by remember { mutableStateOf(true) }
    var text by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({ loading = it }, { ApiClient.api.daily(uid) }) { d = it }
    LaunchedEffect(uid) { reload() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("❓ Вопрос дня", fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Err(vm)
            if (loading && d == null) CircularProgressIndicator()
        }
        d?.let { dd ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), Arrangement.spacedBy(8.dp)) {
                        Text(dd.question.text, fontSize = 18.sp)
                        if (dd.my_answer == null) {
                            OutlinedTextField(text, { text = it }, Modifier.fillMaxWidth(),
                                label = { Text("Ваш ответ") })
                            Button({
                                scope.launch {
                                    try {
                                        ApiClient.api.answer(AnswerReq(uid, text))
                                        text = ""
                                        reload()
                                    } catch (e: Exception) { vm.error = e.message }
                                }
                            }, enabled = text.isNotBlank()) { Text("Отправить") }
                        } else {
                            Text("Вы: ${dd.my_answer}")
                            Text(if (dd.partner_answer != null)
                                "Партнёр: ${dd.partner_answer}"
                            else "Партнёр ещё отвечает…",
                                fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
            item {
                OutlinedButton(toQuizzes, Modifier.fillMaxWidth()) {
                    Text("🎮 К викторинам")
                }
            }
            item {
                OutlinedButton(onPacks, Modifier.fillMaxWidth()) {
                    Text("📚 Темы вопросов")
                }
            }
        }
    }
}

// ---------- викторины ----------
@Composable
fun QuizListScreen(vm: AppVm, open: (Int) -> Unit) {
    var list by remember { mutableStateOf<List<QuizShort>?>(null) }
    LaunchedEffect(Unit) {
        vm.io({}, { ApiClient.api.quizzes() }) { list = it }
    }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("🎮 Викторины", fontSize = 24.sp, fontWeight = FontWeight.Bold); Err(vm) }
        list?.forEach { q ->
            item {
                Card(Modifier.fillMaxWidth(), onClick = { open(q.id) }) {
                    Column(Modifier.padding(16.dp)) {
                        Text(q.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text("Вопросов: ${q.questions}")
                    }
                }
            }
        }
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
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text(q?.title ?: "…", fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Err(vm)
            res?.let {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(if (it.compatibility == null) "Ответьте оба — увидите результат"
                        else "Совместимость: ${it.compatibility}%",
                            fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Text("Вместе отвечено: ${it.answered_together}/${it.total}")
                    }
                }
            }
        }
        q?.questions?.forEach { qq ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), Arrangement.spacedBy(4.dp)) {
                        Row(Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(qq.text, fontWeight = FontWeight.Bold,
                                modifier = Modifier.weight(1f))
                            if (qq.partner_answered) Text("💜")
                        }
                        qq.options.forEachIndexed { i, opt ->
                            Row {
                                RadioButton(qq.my_option == i, {
                                    scope.launch {
                                        try {
                                            ApiClient.api.quizAnswer(
                                                id, QuizAnsReq(uid, qq.id, i))
                                            reload()
                                        } catch (e: Exception) { vm.error = e.message }
                                    }
                                })
                                Text(opt, Modifier.padding(top = 12.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}

// ---------- идеи ----------
@Composable
fun IdeasScreen(vm: AppVm) {
    var list by remember { mutableStateOf<List<Idea>?>(null) }
    var lucky by remember { mutableStateOf<Idea?>(null) }
    var title by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.ideas() }) { list = it }
    LaunchedEffect(Unit) { reload() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("💡 Идеи свиданий", fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Err(vm)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button({
                    scope.launch {
                        try { lucky = ApiClient.api.ideaRandom() }
                        catch (e: Exception) { vm.error = e.message }
                    }
                }) { Text("🎲 Мне повезёт") }
            }
            lucky?.let {
                Card(Modifier.fillMaxWidth().padding(top = 8.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text(it.title, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Text("${it.category} • ${it.budget}")
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
            OutlinedTextField(title, { title = it }, Modifier.fillMaxWidth(),
                label = { Text("Своя идея") })
            Button({
                scope.launch {
                    try {
                        ApiClient.api.ideaAdd(IdeaReq(title))
                        title = ""
                        reload()
                    } catch (e: Exception) { vm.error = e.message }
                }
            }, enabled = title.isNotBlank()) { Text("Добавить") }
        }
        list?.forEach { idea ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(Modifier.weight(1f)) {
                            Text(idea.title, fontWeight = FontWeight.Bold)
                            Text("${idea.category} • ${idea.budget}")
                        }
                        Checkbox(idea.done == 1, {
                            scope.launch {
                                try {
                                    ApiClient.api.ideaDone(idea.id, it)
                                    reload()
                                } catch (e: Exception) { vm.error = e.message }
                            }
                        })
                    }
                }
            }
        }
    }
}

// ---------- журнал ----------
@Composable
fun JournalScreen(vm: AppVm) {
    val uid = vm.userId ?: return
    var list by remember { mutableStateOf<List<JournalEntry>?>(null) }
    var title by remember { mutableStateOf("") }
    var text by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.journal(uid) }) { list = it }
    LaunchedEffect(uid) { reload() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("📖 Общий журнал", fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Err(vm)
            OutlinedTextField(title, { title = it }, Modifier.fillMaxWidth(),
                label = { Text("Заголовок момента") })
            OutlinedTextField(text, { text = it }, Modifier.fillMaxWidth(),
                label = { Text("Что запомнилось?") })
            Button({
                scope.launch {
                    try {
                        ApiClient.api.journalAdd(JournalReq(uid, title, text))
                        title = ""; text = ""
                        reload()
                    } catch (e: Exception) { vm.error = e.message }
                }
            }, enabled = title.isNotBlank()) { Text("Сохранить момент") }
        }
        list?.forEach { j ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), Arrangement.spacedBy(4.dp)) {
                        Text(j.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        if (j.text.isNotBlank()) Text(j.text)
                        Text("${j.author} • ${j.ts}", color = MaterialTheme.colorScheme.secondary)
                    }
                }
            }
        }
    }
}

// ---------- темы вопросов ----------
@Composable
fun PackListScreen(vm: AppVm, open: (Int) -> Unit) {
    val uid = vm.userId ?: return
    var list by remember { mutableStateOf<List<PackShort>?>(null) }
    LaunchedEffect(uid) { vm.io({}, { ApiClient.api.packs(uid) }) { list = it } }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("📚 Темы вопросов", fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Text("Ответ партнёра виден, когда ответили оба.")
            Err(vm)
        }
        list?.forEach { p ->
            item {
                Card(Modifier.fillMaxWidth(), onClick = { open(p.id) }) {
                    Column(Modifier.padding(16.dp), Arrangement.spacedBy(4.dp)) {
                        Text(p.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text(p.description)
                        Text("Ваших: ${p.answered_by_me}/${p.total} • Вместе: ${p.answered_together}")
                    }
                }
            }
        }
    }
}

@Composable
fun PackScreen(vm: AppVm, id: Int) {
    val uid = vm.userId ?: return
    var p by remember { mutableStateOf<PackResp?>(null) }
    var drafts by remember { mutableStateOf<Map<Int, String>>(emptyMap()) }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.pack(id, uid) }) { p = it }
    LaunchedEffect(id) { reload() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text(p?.title ?: "…", fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Err(vm)
        }
        p?.questions?.forEach { q ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), Arrangement.spacedBy(4.dp)) {
                        Row(Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(q.text, fontWeight = FontWeight.Bold,
                                modifier = Modifier.weight(1f))
                            if (q.partner_answered) Text("💜")
                        }
                        if (q.my_answer == null) {
                            OutlinedTextField(
                                drafts[q.id] ?: "", { drafts = drafts + (q.id to it) },
                                Modifier.fillMaxWidth(), label = { Text("Ваш ответ") })
                            Button({
                                scope.launch {
                                    try {
                                        ApiClient.api.packAnswer(
                                            id, PackAnsReq(uid, q.id, drafts[q.id] ?: ""))
                                        reload()
                                    } catch (e: Exception) { vm.error = e.message }
                                }
                            }, enabled = !(drafts[q.id].isNullOrBlank())) { Text("Отправить") }
                        } else {
                            Text("Вы: ${q.my_answer}")
                            Text(if (q.partner_answer != null)
                                "Партнёр: ${q.partner_answer}"
                            else "Партнёр ещё отвечает…",
                                fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}

// ---------- события ----------
@Composable
fun EventsScreen(vm: AppVm) {
    val uid = vm.userId ?: return
    var list by remember { mutableStateOf<List<EventResp>?>(null) }
    var title by remember { mutableStateOf("") }
    var date by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun reload() = vm.io({}, { ApiClient.api.events(uid) }) { list = it }
    LaunchedEffect(uid) { reload() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp),
               verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("⏳ Обратный отсчёт", fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Err(vm)
            OutlinedTextField(title, { title = it }, Modifier.fillMaxWidth(),
                label = { Text("Событие (годовщина, поездка…)") })
            OutlinedTextField(date, { date = it }, Modifier.fillMaxWidth(),
                label = { Text("Дата ГГГГ-ММ-ДД") })
            Button({
                scope.launch {
                    try {
                        ApiClient.api.eventAdd(EventReq(uid, title, date))
                        title = ""; date = ""
                        reload()
                    } catch (e: Exception) { vm.error = e.message }
                }
            }, enabled = title.isNotBlank() && date.isNotBlank()) { Text("Добавить") }
        }
        list?.forEach { e ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(e.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text(if (e.days_left >= 0) "Осталось дней: ${e.days_left}"
                        else "Было ${-e.days_left} дн. назад")
                        Text(e.date, color = MaterialTheme.colorScheme.secondary)
                    }
                }
            }
        }
    }
}
