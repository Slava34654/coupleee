package com.couplejoy.app

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.couplejoy.app.api.ApiClient
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
    private lateinit var web: WebView
    private var fileCb: ValueCallback<Array<Uri>>? = null

    private val pickFile =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
            val cb = fileCb
            fileCb = null
            if (r.resultCode == Activity.RESULT_OK) {
                val u = r.data?.data
                val clip = r.data?.clipData
                val arr = when {
                    u != null -> arrayOf(u)
                    clip != null && clip.itemCount > 0 ->
                        Array(clip.itemCount) { clip.getItemAt(it).uri }
                    else -> null
                }
                cb?.onReceiveValue(arr)
            } else {
                cb?.onReceiveValue(null)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("cj", Context.MODE_PRIVATE)
        val baseUrl = prefs.getString("base_url", ApiClient.DEFAULT_URL)!!
        ApiClient.init(baseUrl)
        scheduleWidget(this)

        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.loadWithOverviewMode = true
            settings.useWideViewPort = true
            settings.mediaPlaybackRequiresUserGesture = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    v: WebView, req: WebResourceRequest
                ): Boolean = false
            }
            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    v: WebView,
                    cb: ValueCallback<Array<Uri>>,
                    params: FileChooserParams
                ): Boolean {
                    fileCb?.onReceiveValue(null)
                    fileCb = cb
                    val i = Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "image/*"
                    }
                    pickFile.launch(Intent.createChooser(i, "Фото"))
                    return true
                }
            }
        }
        setContentView(web)
        if (savedInstanceState != null) web.restoreState(savedInstanceState)
        else web.loadUrl(baseUrl)

        onBackPressedDispatcher.addCallback(
            this,
            object : androidx.activity.OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (web.canGoBack()) web.goBack()
                    else {
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                    }
                }
            }
        )
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (::web.isInitialized) web.saveState(outState)
    }
}
