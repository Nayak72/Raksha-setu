package com.raksha.setu

import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

object AckSender {
    private const val TAG = "AckSender"
    private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    private val client = OkHttpClient()

    fun sendAck(serverIp: String, deviceId: String, alertId: String) {
        if (serverIp.isEmpty()) { Log.w(TAG, "No server_ip"); return }
        val url = "http://$serverIp:8000/api/v1/acknowledge"
        val payload = JSONObject().apply {
            put("device_id", deviceId); put("alert_id", alertId); put("status", "received")
        }
        val body = payload.toString().toRequestBody(JSON_MEDIA)
        val request = Request.Builder().url(url).post(body).build()
        Log.i(TAG, "Sending ACK to $url")
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { Log.e(TAG, "ACK failed: ${e.message}") }
            override fun onResponse(call: Call, response: Response) {
                response.use { Log.i(TAG, "ACK response: ${response.code}") }
            }
        })
    }
}
