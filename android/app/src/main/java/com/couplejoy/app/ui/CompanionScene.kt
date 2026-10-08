package com.couplejoy.app.ui

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.google.gson.Gson

@androidx.annotation.Keep
private class CompanionBridge(val onReady: () -> Unit, val onPet: () -> Unit, val onError: () -> Unit) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun ready() { main.post { onReady() } }
    @JavascriptInterface fun pet() { main.post { onPet() } }
    @JavascriptInterface fun error(message: String) { main.post { onError() } }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun CompanionScene(state: CareState, animation: String, eventId: Int, modifier: Modifier,
                   onPet: () -> Unit, onReady: () -> Unit, onError: () -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val pet by rememberUpdatedState(onPet)
    val readyCallback by rememberUpdatedState(onReady)
    val errorCallback by rememberUpdatedState(onError)
    var ready by remember { mutableStateOf(false) }
    val view = remember {
        WebView.setWebContentsDebuggingEnabled(
            context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0
        )
        WebView(context).apply {
            setBackgroundColor(Color.rgb(245, 230, 229))
            settings.javaScriptEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.blockNetworkLoads = true
            isVerticalScrollBarEnabled = false
            isHorizontalScrollBarEnabled = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?) = true
            }
            addJavascriptInterface(CompanionBridge(
                { ready = true; readyCallback() }, { pet() }, { errorCallback() }
            ), "Companion")
            loadUrl("file:///android_asset/companion/index.html")
        }
    }
    val payload = remember(state, animation, eventId) {
        Gson().toJson(mapOf(
            "type" to state.type, "level" to state.level, "energy" to state.energy,
            "joy" to state.joy, "hunger" to state.hunger, "clean" to state.clean,
            "sleeping" to state.sleeping, "room" to state.room,
            "accessory" to state.accessory, "animation" to animation, "eventId" to eventId
        ))
    }
    LaunchedEffect(ready, payload) {
        if (ready) view.evaluateJavascript("window.setCompanion && window.setCompanion($payload)", null)
    }
    DisposableEffect(view, lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_PAUSE -> { view.evaluateJavascript("window.pauseCompanion && window.pauseCompanion()", null); view.onPause() }
                Lifecycle.Event.ON_RESUME -> { view.onResume(); view.evaluateJavascript("window.resumeCompanion && window.resumeCompanion()", null) }
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            view.removeJavascriptInterface("Companion")
            view.stopLoading()
            view.destroy()
        }
    }
    AndroidView(factory = { view }, modifier = modifier)
}
