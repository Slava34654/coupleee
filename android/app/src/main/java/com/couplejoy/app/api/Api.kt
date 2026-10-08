package com.couplejoy.app.api

import okhttp3.Interceptor
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

// Для эмулятора бэкенд на ПК доступен по 10.0.2.2.
// Для реального телефона в той же Wi-Fi сети — IP компьютера, напр. http://192.168.1.5:8000/
const val BASE_URL = "http://10.0.2.2:8000/"

// ---------- модели (имена полей = JSON бэкенда) ----------
data class PairResp(val user_id: Int, val pair_code: String?, val partner_id: Int? = null,
                     val token: String? = null)
data class PairReq(val name: String, val birth: String = "", val avatar: String = "",
                   val since: String = "")
data class JoinReq(val name: String, val code: String, val birth: String = "", val avatar: String = "")
data class RegisterReq(val email: String, val password: String)
data class PairSetupReq(val user_id: Int, val name: String, val birth: String = "",
                        val avatar: String = "", val since: String = "",
                        val partner_code: String = "")
data class LoginReq(val email: String, val password: String)
data class AuthResp(val user_id: Int, val pair_code: String, val partner_id: Int? = null,
                    val token: String, val name: String, val birth: String = "",
                    val avatar: String = "", val together_since: String = "",
                    val pair_ready: Boolean = true)
data class MoodInfo(val mood: String, val note: String, val ts: String)
data class Partner(val id: Int, val name: String, val birth: String = "",
                  val avatar: String = "", val age: Int? = null)
data class MeResp(val id: Int, val name: String, val pair_code: String,
                 val partner: Partner?, val days_together: Int, val streak: Int,
                 val my_mood: MoodInfo?, val partner_mood: MoodInfo?,
                 val together_since: String = "")
data class TogetherIn(val user_id: Int, val date: String)
data class TogetherOut(val date: String, val days: Int)
data class MoodReq(val user_id: Int, val mood: String, val note: String = "")
data class OkResp(val ok: Boolean)
data class DailyQ(val date: String, val index: Int, val text: String)
data class DailyResp(val question: DailyQ, val my_answer: String?,
                    val partner_answer: String?, val partner_answered: Boolean)
data class AnswerReq(val user_id: Int, val text: String)
data class QuizShort(val id: Int, val title: String, val questions: Int)
data class QuizQ(val id: Int, val text: String, val options: List<String>,
                 val my_option: Int?, val partner_answered: Boolean)
data class QuizResp(val id: Int, val title: String, val questions: List<QuizQ>)
data class QuizAnsReq(val user_id: Int, val qid: Int, val option: Int)
data class QuizResult(val compatibility: Int?, val answered_together: Int, val total: Int)
data class Idea(val id: Int, val title: String, val category: String,
                val budget: String, val done: Int)
data class IdeaReq(val title: String, val category: String = "", val budget: String = "")
data class IdResp(val id: Int)
data class JournalReq(val user_id: Int, val title: String, val text: String = "")
data class JournalEntry(val id: Int, val user_id: Int, val title: String,
                       val text: String, val ts: String, val author: String)
data class EventReq(val user_id: Int, val title: String, val date: String)
data class EventResp(val id: Int, val title: String, val date: String, val days_left: Int)
data class PhotoResp(val url: String)
data class WidgetPhoto(val photo: String, val caption: String, val ts: String)
data class WidgetResp(val mine: WidgetPhoto?, val partner: WidgetPhoto?)
data class WidgetReq(val user_id: Int, val photo: String, val caption: String = "")
data class PackShort(val id: Int, val title: String, val description: String,
                    val kind: String = "short",
                    val total: Int, val answered_by_me: Int, val answered_together: Int)
data class PackQ(val id: Int, val text: String, val my_answer: String?,
                 val my_photo: String? = null,
                 val partner_answered: Boolean, val partner_answer: String?,
                 val partner_photo: String? = null)
data class PackResp(val id: Int, val title: String, val description: String,
                   val kind: String = "short",
                   val questions: List<PackQ>)
data class PackAnsReq(val user_id: Int, val qid: Int, val text: String = "",
                      val photo: String = "")
data class LocationReq(val user_id: Int, val lat: Double, val lon: Double)
data class DistanceResp(val sharing: Boolean, val partner_sharing: Boolean,
                        val km: Double?, val partner_name: String? = null,
                        val partner_age_min: Int? = null)
data class LinkCodeIn(val user_id: Int)
data class LinkCode(val code: String)
data class PremiumOut(val premium: Boolean, val until: String)

interface Api {
    @POST("auth/register") suspend fun register(@Body b: RegisterReq): AuthResp
    @POST("auth/login") suspend fun login(@Body b: LoginReq): AuthResp
    @POST("pair/setup") suspend fun pairSetup(@Body b: PairSetupReq): AuthResp
    @POST("pair") suspend fun pair(@Body b: PairReq): PairResp
    @POST("pair/join") suspend fun join(@Body b: JoinReq): PairResp
    @GET("me") suspend fun me(@Query("user_id") u: Int): MeResp
    @POST("mood") suspend fun mood(@Body b: MoodReq): OkResp
    @GET("daily") suspend fun daily(@Query("user_id") u: Int): DailyResp
    @POST("daily/answer") suspend fun answer(@Body b: AnswerReq): OkResp
    @GET("quizzes") suspend fun quizzes(): List<QuizShort>
    @GET("quiz/{id}") suspend fun quiz(@Path("id") id: Int,
                                       @Query("user_id") u: Int): QuizResp
    @POST("quiz/{id}/answer") suspend fun quizAnswer(@Path("id") id: Int,
                                                     @Body b: QuizAnsReq): OkResp
    @GET("quiz/{id}/result") suspend fun quizResult(@Path("id") id: Int,
                                                    @Query("user_id") u: Int): QuizResult
    @GET("ideas") suspend fun ideas(): List<Idea>
    @GET("idea/random") suspend fun ideaRandom(): Idea
    @POST("ideas") suspend fun ideaAdd(@Body b: IdeaReq): IdResp
    @POST("idea/{id}/done") suspend fun ideaDone(@Path("id") id: Int,
                                                 @Query("done") d: Boolean): OkResp
    @POST("journal") suspend fun journalAdd(@Body b: JournalReq): IdResp
    @GET("journal") suspend fun journal(@Query("user_id") u: Int): List<JournalEntry>
    @POST("events") suspend fun eventAdd(@Body b: EventReq): IdResp
    @GET("events") suspend fun events(@Query("user_id") u: Int): List<EventResp>
    @GET("packs") suspend fun packs(@Query("user_id") u: Int): List<PackShort>
    @GET("pack/{id}") suspend fun pack(@Path("id") id: Int,
                                       @Query("user_id") u: Int): PackResp
    @POST("pack/{id}/answer") suspend fun packAnswer(@Path("id") id: Int,
                                                     @Body b: PackAnsReq): OkResp
    @Multipart @POST("photos") suspend fun upload(@Part file: MultipartBody.Part): PhotoResp
    @POST("widget") suspend fun widgetSend(@Body b: WidgetReq): OkResp
    @GET("widget") suspend fun widget(@Query("user_id") u: Int): WidgetResp
    @POST("location") suspend fun locationSend(@Body b: LocationReq): OkResp
    @DELETE("location") suspend fun locationStop(@Query("user_id") u: Int): OkResp
    @GET("distance") suspend fun distance(@Query("user_id") u: Int): DistanceResp
    @POST("premium/code") suspend fun premiumCode(@Body b: LinkCodeIn): LinkCode
    @GET("premium") suspend fun premium(@Query("user_id") u: Int): PremiumOut
    @POST("together") suspend fun together(@Body b: TogetherIn): TogetherOut
}

object ApiClient {
    const val DEFAULT_URL = "https://ssssw-sladaqqq.amvera.io/"
    const val AUTH_HEADER = "X-Auth-Token"

    /** Токен текущего пользователя. Подставляется в каждый запрос. */
    var authToken: String = ""

    private val authInterceptor = Interceptor { chain ->
        val req = chain.request()
        val t = authToken
        val withAuth = if (t.isNotBlank()) {
            req.newBuilder().header(AUTH_HEADER, t).build()
        } else req
        chain.proceed(withAuth)
    }
    private val http = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .build()

    private fun build(url: String): Api = Retrofit.Builder()
        .baseUrl(url)
        .client(http)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(Api::class.java)
    var api: Api = build(DEFAULT_URL)
    fun forUrl(url: String): Api {
        val u = if (url.endsWith("/")) url else "$url/"
        return build(u)
    }
    fun init(url: String) {
        api = forUrl(url.ifBlank { DEFAULT_URL })
    }
}
