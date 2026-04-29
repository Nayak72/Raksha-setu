package com.raksha.setu

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class FcmListenerService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "FcmListenerService"
    }

    override fun onNewToken(token: String) {
        Log.d(TAG, "Refreshed FCM token: $token")
        // TODO: Send this token to the backend if targeted pushes are needed.
        // Currently, we use topic messaging ("alerts") so individual tokens are optional.
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        Log.d(TAG, "From: ${remoteMessage.from}")

        // Check if message contains a data payload.
        if (remoteMessage.data.isNotEmpty()) {
            Log.d(TAG, "Message data payload: ${remoteMessage.data}")
            
            val alertId = remoteMessage.data["alert_id"] ?: ""
            val zone = remoteMessage.data["zone"] ?: ""
            val severity = remoteMessage.data["severity"] ?: "MEDIUM"
            val message = remoteMessage.data["message"] ?: ""
            val timestamp = remoteMessage.data["timestamp"] ?: ""
            val serverIp = remoteMessage.data["server_ip"] ?: ""
            
            if (alertId.isNotEmpty() && message.isNotEmpty()) {
                AlertManager.handleAlert(
                    context = this,
                    alertId = alertId,
                    zone = zone,
                    severity = severity,
                    message = message,
                    timestamp = timestamp,
                    serverIp = serverIp
                )
            }
        }
    }
}
