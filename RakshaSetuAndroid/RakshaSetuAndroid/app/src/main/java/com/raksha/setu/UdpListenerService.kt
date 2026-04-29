package com.raksha.setu

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket

/**
 * Foreground Service that continuously listens for UDP broadcast packets on port 5005.
 * Runs with a persistent notification to prevent the OS from killing it.
 * Parses incoming JSON payloads and routes them to AlertManager.
 */
class UdpListenerService : Service() {

    companion object {
        private const val TAG = "UdpListenerService"
        private const val UDP_PORT = 5005
        private const val BUFFER_SIZE = 4096
        private const val CHANNEL_ID = "raksha_setu_listener"
        private const val NOTIFICATION_ID = 1
    }

    private var isRunning = false
    private var listenerThread: Thread? = null
    private var socket: DatagramSocket? = null
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i(TAG, "Service starting — binding to UDP port $UDP_PORT")

        // Start as foreground service with persistent notification
        val notification = buildNotification("Raksha-Setu is active — listening for alerts")
        startForeground(NOTIFICATION_ID, notification)

        // Acquire partial wake lock to keep CPU running
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "RakshaSetu::UdpListenerWakeLock"
        ).apply {
            acquire(60 * 60 * 1000L) // 1 hour max, re-acquired on each alert
        }

        // Start the UDP listener thread
        if (!isRunning) {
            isRunning = true
            listenerThread = Thread(::udpListenLoop).apply {
                name = "UdpListenerThread"
                isDaemon = true
                start()
            }
        }

        return START_STICKY // Restart if killed by OS
    }

    /**
     * Main UDP listening loop — runs on a background thread.
     * Continuously receives packets, parses JSON, and dispatches to AlertManager.
     */
    private fun udpListenLoop() {
        try {
            socket = DatagramSocket(UDP_PORT).apply {
                broadcast = true
                reuseAddress = true
            }
            Log.i(TAG, "UDP socket bound to port $UDP_PORT")

            val buffer = ByteArray(BUFFER_SIZE)

            while (isRunning) {
                try {
                    val packet = DatagramPacket(buffer, buffer.size)
                    socket?.receive(packet) // Blocks until a packet arrives

                    val data = String(packet.data, 0, packet.length, Charsets.UTF_8)
                    Log.d(TAG, "Packet received (${packet.length} bytes) from ${packet.address}")

                    handlePacket(data)

                } catch (e: Exception) {
                    if (isRunning) {
                        Log.e(TAG, "Error receiving UDP packet: ${e.message}")
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create UDP socket: ${e.message}")
        } finally {
            socket?.close()
            Log.i(TAG, "UDP socket closed")
        }
    }

    /**
     * Parse and validate the received JSON packet, then pass to AlertManager.
     */
    private fun handlePacket(data: String) {
        try {
            val json = JSONObject(data)

            // Validate mandatory fields
            val type = json.optString("type", "")
            if (type != "ALERT") {
                Log.w(TAG, "Ignoring non-ALERT packet: type=$type")
                return
            }

            val alertId = json.optString("alert_id", "")
            val zone = json.optString("zone", "")
            val severity = json.optString("severity", "MEDIUM")
            val message = json.optString("message", "")
            val timestamp = json.optString("timestamp", "")
            val serverIp = json.optString("server_ip", "")

            if (alertId.isEmpty() || message.isEmpty()) {
                Log.w(TAG, "Ignoring malformed ALERT: missing alert_id or message")
                return
            }

            Log.i(TAG, "Valid ALERT received: id=$alertId, severity=$severity, zone=$zone")

            // Dispatch to AlertManager
            AlertManager.handleAlert(
                context = this,
                alertId = alertId,
                zone = zone,
                severity = severity,
                message = message,
                timestamp = timestamp,
                serverIp = serverIp
            )

        } catch (e: Exception) {
            Log.e(TAG, "Invalid JSON packet — ignoring: ${e.message}")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Raksha-Setu Listener",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent notification for UDP alert listener"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(content: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Raksha-Setu")
            .setContentText(content)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    override fun onDestroy() {
        Log.i(TAG, "Service stopping")
        isRunning = false
        socket?.close()
        listenerThread?.interrupt()
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
