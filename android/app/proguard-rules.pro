# Enrwine: правила R8 для релиза.
# Модели API читаются через Gson рефлексией — не трогать.
-keep class com.couplejoy.app.api.** { *; }
# WorkManager создаёт воркеры рефлексией.
-keep public class * extends androidx.work.Worker {
    public <init>(android.content.Context, androidx.work.WorkerParameters);
}
-keep public class * extends androidx.work.CoroutineWorker {
    public <init>(android.content.Context, androidx.work.WorkerParameters);
}
# Glance-виджеты.
-keep public class * extends androidx.glance.appwidget.GlanceAppWidgetReceiver
-keep class com.couplejoy.app.widget.** { *; }
# Retrofit/OkHttp/Gson/Coil тянут свои consumer-правила сами, это страховка.
-dontwarn retrofit2.**
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn com.google.gson.**
-dontwarn coil.**
