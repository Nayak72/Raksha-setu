package com.raksha.setu

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * AlertManager — receives parsed UDP data, validates, deduplicates,
 * and triggers the full-screen AlertActivity.
 */
object AlertManager {

    private const val TAG = "AlertManager"

    // Track seen alert IDs to prevent duplicate alerts
    private val seenAlertIds = mutableSetOf<String>()

    /**
     * Handle an incoming validated alert.
     * Deduplicates by alert_id and launches the full-screen alert UI.
     */
    fun handleAlert(
        context: Context,
        alertId: String,
        zone: String,
        severity: String,
        message: String,
        timestamp: String,
        serverIp: String
    ) {
        // Deduplicate — ignore if already seen
        if (seenAlertIds.contains(alertId)) {
            Log.i(TAG, "Duplicate alert_id=$alertId — ignoring")
            return
        }
        seenAlertIds.add(alertId)

        // Cap the set size to prevent memory issues
        if (seenAlertIds.size > 500) {
            val iterator = seenAlertIds.iterator()
            repeat(100) { if (iterator.hasNext()) { iterator.next(); iterator.remove() } }
        }

        Log.i(TAG, "🚨 New ALERT: id=$alertId, zone=$zone, severity=$severity")

        // Wake the device
        wakeDevice(context)

        // Create intent for AlertActivity
        val intent = Intent(context, AlertActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra("alert_id", alertId)
            putExtra("zone", zone)
            putExtra("severity", severity)
            putExtra("message", message)
            putExtra("timestamp", timestamp)
            putExtra("server_ip", serverIp)
        }

        // ── PRIMARY: Directly launch AlertActivity ──
        // This is the reliable path — startActivity() works from services
        // and foreground contexts on all Android versions.
        try {
            context.startActivity(intent)
            Log.i(TAG, "AlertActivity launched directly via startActivity()")
        } catch (e: Exception) {
            Log.e(TAG, "Direct startActivity() failed: ${e.message}")
        }

        // ── SECONDARY: Post notification as backup/visible record ──
        val pendingIntent = PendingIntent.getActivity(
            context,
            alertId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val channelId = "raksha_setu_alerts"
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Emergency Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical disaster alert notifications"
                enableVibration(true)
                enableLights(true)
            }
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(context, channelId)
            .setContentTitle("🚨 EMERGENCY ALERT — $severity")
            .setContentText("$zone: $message")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setFullScreenIntent(pendingIntent, true)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(alertId.hashCode(), notification)
    }

    /**
     * Wake the device screen using a WakeLock.
     */
    private fun wakeDevice(context: Context) {
        try {
            val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            val wakeLock = pm.newWakeLock(
                PowerManager.FULL_WAKE_LOCK or
                        PowerManager.ACQUIRE_CAUSES_WAKEUP or
                        PowerManager.ON_AFTER_RELEASE,
                "RakshaSetu::AlertWakeLock"
            )
            wakeLock.acquire(30_000L) // Hold for 30 seconds
            Log.d(TAG, "Device wake lock acquired")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to acquire wake lock: ${e.message}")
        }
    }

    /**
     * Clear seen alerts (for testing/reset).
     */
    fun clearHistory() {
        seenAlertIds.clear()
    }
}
