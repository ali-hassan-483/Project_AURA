package com.aura.companion

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AuraApiClient(private var baseUrl: String = "http://10.0.2.2:8000") {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    fun updateBaseUrl(newUrl: String) {
        this.baseUrl = newUrl.trimEnd('/')
    }

    suspend fun sendMessage(userPhone: String, message: String): Result<AuraResponse> = withContext(Dispatchers.IO) {
        try {
            val json = JSONObject().apply {
                put("message", message)
                put("phone", userPhone)
                put("name", "Android User")
            }

            val requestBody = json.toString().toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url("$baseUrl/api/admin/simulator/chat")
                .post(requestBody)
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                return@withContext Result.failure(Exception("HTTP Error ${response.code}"))
            }

            val responseBody = response.body?.string() ?: return@withContext Result.failure(Exception("Empty body"))
            val resJson = JSONObject(responseBody)

            val reply = resJson.optString("reply", "...")
            val imageUrl = if (resJson.optBoolean("has_image")) {
                val path = resJson.optString("image_url")
                if (path.startsWith("http")) path else "$baseUrl$path"
            } else null

            val voiceUrl = if (resJson.optBoolean("has_voice")) {
                val path = resJson.optString("voice_url")
                if (path.startsWith("http")) path else "$baseUrl$path"
            } else null

            Result.success(AuraResponse(reply, imageUrl, voiceUrl))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

data class AuraResponse(
    val reply: String,
    val imageUrl: String?,
    val voiceUrl: String?
)
