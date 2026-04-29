package com.raksha.setu

import android.animation.ArgbEvaluator
import android.animation.ValueAnimator
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.os.*
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

/**
 * Full-screen alert activity that displays over the lock screen.
 * Features:
 *   - Red flashing background
 *   - Loud alarm sound (looping)
 *   - Continuous vibration
 *   - Zone, severity, and message display
 *   - Acknowledge button to dismiss and send ACK
 */
class AlertActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "AlertActivity"
        private const val ALERT_CHANNEL_ID = "raksha_setu_alerts"
        private const val ALERT_NOTIFICATION_ID = 2000
    }

    private var mediaPlayer: MediaPlayer? = null
    private var vibrator: Vibrator? = null
    private var flashAnimator: ValueAnimator? = null

    private var alertId: String = ""
    private var serverIp: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Show over lock screen
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                        WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                        WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            )
        }

        // Keep screen on
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        setContentView(R.layout.activity_alert)

        // Extract alert data from intent
        alertId = intent.getStringExtra("alert_id") ?: "unknown"
        val zone = intent.getStringExtra("zone") ?: "Unknown Zone"
        val severity = intent.getStringExtra("severity") ?: "MEDIUM"
        val message = intent.getStringExtra("message") ?: "Alert received"
        val timestamp = intent.getStringExtra("timestamp") ?: ""
        serverIp = intent.getStringExtra("server_ip") ?: ""

        // Set UI content
        findViewById<TextView>(R.id.alertZone).text = "Zone: $zone"
        findViewById<TextView>(R.id.alertSeverity).text = "Severity: $severity"
        findViewById<TextView>(R.id.alertMessage).text = message
        findViewById<TextView>(R.id.alertTimestamp).text = "Time: $timestamp"

        // Severity-based styling
        val severityView = findViewById<TextView>(R.id.alertSeverity)
        when (severity) {
            "CRITICAL" -> severityView.setTextColor(ContextCompat.getColor(this, android.R.color.holo_red_light))
            "HIGH" -> severityView.setTextColor(ContextCompat.getColor(this, android.R.color.holo_orange_dark))
            "MEDIUM" -> severityView.setTextColor(ContextCompat.getColor(this, android.R.color.holo_orange_light))
            else -> severityView.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_dark))
        }

        // Acknowledge button
        findViewById<Button>(R.id.ackButton).setOnClickListener {
            acknowledgeAlert()
        }

        // Start alarm effects
        startFlashingBackground()
        startAlarmSound()
        startVibration()

        Log.i(TAG, "Alert displayed: id=$alertId, zone=$zone, severity=$severity")
    }

    /**
     * Flash the background between red and dark red.
     */
    private fun startFlashingBackground() {
        val rootView = findViewById<View>(R.id.alertRoot)
        val colorFrom = 0xFFCC0000.toInt() // Dark red
        val colorTo = 0xFFFF0000.toInt()    // Bright red

        flashAnimator = ValueAnimator.ofObject(ArgbEvaluator(), colorFrom, colorTo).apply {
            duration = 500
            repeatMode = ValueAnimator.REVERSE
            repeatCount = ValueAnimator.INFINITE
            addUpdateListener { animator ->
                rootView.setBackgroundColor(animator.animatedValue as Int)
            }
            start()
        }
    }

    /**
     * Play the default alarm ringtone on loop at maximum volume.
     */
    private fun startAlarmSound() {
        try {
            // Set volume to max
            val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
            audioManager.setStreamVolume(AudioManager.STREAM_ALARM, maxVolume, 0)

            val alarmUri = android.net.Uri.parse("android.resource://" + packageName + "/" + R.raw.sos_sound)

            mediaPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                setDataSource(this@AlertActivity, alarmUri)
                isLooping = true
                prepare()
                start()
            }
            Log.d(TAG, "Alarm sound started")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start alarm sound: ${e.message}")
        }
    }

    /**
     * Start continuous vibration pattern.
     */
    private fun startVibration() {
        vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vibratorManager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }

        // Pattern: wait 0ms, vibrate 1s, pause 500ms — repeat indefinitely
        val pattern = longArrayOf(0, 1000, 500, 1000, 500)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator?.vibrate(VibrationEffect.createWaveform(pattern, 0))
        } else {
            @Suppress("DEPRECATION")
            vibrator?.vibrate(pattern, 0)
        }
        Log.d(TAG, "Vibration started")
    }

    /**
     * Acknowledge the alert: stop all effects and send ACK to backend.
     */
    private fun acknowledgeAlert() {
        Log.i(TAG, "Alert acknowledged: id=$alertId")

        // Stop all alarm effects
        stopEffects()

        // Dismiss notification
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.cancel(alertId.hashCode())

        // Send ACK to backend
        val deviceId = DeviceIdentifier.getDeviceId(this)
        AckSender.sendAck(
            serverIp = serverIp,
            deviceId = deviceId,
            alertId = alertId
        )

        // Update UI
        findViewById<View>(R.id.alertRoot).setBackgroundColor(0xFF1B5E20.toInt()) // Dark green
        findViewById<TextView>(R.id.alertMessage).text = "✅ Alert Acknowledged\nACK sent to server"
        findViewById<Button>(R.id.ackButton).isEnabled = false

        // Close after 3 seconds
        Handler(Looper.getMainLooper()).postDelayed({
            finish()
        }, 3000)
    }

    private fun stopEffects() {
        flashAnimator?.cancel()
        mediaPlayer?.let {
            if (it.isPlaying) it.stop()
            it.release()
        }
        mediaPlayer = null
        vibrator?.cancel()
    }

    override fun onDestroy() {
        stopEffects()
        super.onDestroy()
    }
}
