package com.raksha.setu

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessaging
import android.util.Log

/**
 * Main launcher activity for Raksha-Setu.
 * Starts the UDP listener foreground service and shows status.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var deviceIdText: TextView
    private lateinit var startButton: Button
    private lateinit var stopButton: Button

    companion object {
        private const val NOTIFICATION_PERMISSION_CODE = 1001
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        deviceIdText = findViewById(R.id.deviceIdText)
        startButton = findViewById(R.id.startButton)
        stopButton = findViewById(R.id.stopButton)

        // Show device ID
        val deviceId = DeviceIdentifier.getDeviceId(this)
        deviceIdText.text = "Device ID: ${deviceId.take(8)}..."

        // Request notification permission for Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    NOTIFICATION_PERMISSION_CODE
                )
            }
        }

        startButton.setOnClickListener {
            startListenerService()
            updateStatus(true)
        }

        stopButton.setOnClickListener {
            stopListenerService()
            updateStatus(false)
        }

        // Auto-start the service
        startListenerService()
        updateStatus(true)

        // Firebase Cloud Messaging: Get Token & Subscribe to Alerts
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.w("MainActivity", "Fetching FCM registration token failed", task.exception)
                return@addOnCompleteListener
            }
            Log.d("MainActivity", "FCM Token: ${task.result}")
        }

        FirebaseMessaging.getInstance().subscribeToTopic("alerts")
            .addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    Log.d("MainActivity", "Subscribed to FCM topic: alerts")
                } else {
                    Log.e("MainActivity", "Failed to subscribe to FCM topic: alerts")
                }
            }
    }

    private fun startListenerService() {
        val intent = Intent(this, UdpListenerService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopListenerService() {
        val intent = Intent(this, UdpListenerService::class.java)
        stopService(intent)
    }

    private fun updateStatus(active: Boolean) {
        if (active) {
            statusText.text = "🟢 Raksha-Setu is ACTIVE\nListening on UDP port 5005"
            statusText.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_dark))
            startButton.isEnabled = false
            stopButton.isEnabled = true
        } else {
            statusText.text = "🔴 Raksha-Setu is STOPPED"
            statusText.setTextColor(ContextCompat.getColor(this, android.R.color.holo_red_dark))
            startButton.isEnabled = true
            stopButton.isEnabled = false
        }
    }
}
