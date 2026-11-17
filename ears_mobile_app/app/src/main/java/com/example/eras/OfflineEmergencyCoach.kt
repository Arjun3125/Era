package com.example.eras

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import androidx.core.app.NotificationCompat
import java.util.concurrent.ConcurrentLinkedQueue

class OfflineEmergencyCoach(private val context: Context) {

    private val acuteStressKeywords = setOf(
        "panic", "can't breathe", "cant breathe", "overwhelmed", "heart racing",
        "too much", "breaking down", "freaking out", "anxious", "so stressed",
        "ghabrahamat", "pareshan", "tens tension"
    )

    private val recentTriggers = ConcurrentLinkedQueue<Long>()
    private val triggerWindowMs = 5 * 60 * 1000L
    private val triggerThreshold = 2

    init {
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "ears_offline_coach",
                "Era Offline Coach Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Emergency decompression coaching alerts when offline"
            }
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    fun analyzeSegmentOffline(speaker: String, text: String, isOffline: Boolean) {
        if (!isOffline || speaker != "0") return

        val lowerText = text.lowercase()
        var matchFound = false

        for (kw in acuteStressKeywords) {
            if (lowerText.contains(kw)) {
                matchFound = true
                Log.w("OfflineCoach", "Detected offline stress keyword: '$kw'")
                break
            }
        }

        if (matchFound) {
            val now = System.currentTimeMillis()
            recentTriggers.add(now)
            cleanOldTriggers(now)

            if (recentTriggers.size >= triggerThreshold) {
                triggerDecompressionIntervention()
                recentTriggers.clear()
            }
        }
    }

    private fun cleanOldTriggers(now: Long) {
        while (!recentTriggers.isEmpty()) {
            val ts = recentTriggers.peek() ?: break
            if (now - ts > triggerWindowMs) {
                recentTriggers.poll()
            } else {
                break
            }
        }
    }

    private fun triggerDecompressionIntervention() {
        Log.i("OfflineCoach", "Firing offline emergency decompression alert!")

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                val vibrator = vibratorManager.defaultVibrator
                vibrator.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 400, 200, 400), -1))
            } else {
                @Suppress("DEPRECATION")
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                vibrator.vibrate(longArrayOf(0, 400, 200, 400), -1)
            }
        } catch (e: Exception) {
            Log.e("OfflineCoach", "Vibration failed: ${e.message}")
        }

        val notification = NotificationCompat.Builder(context, "ears_offline_coach")
            .setContentTitle("Era Offline Coach: Take a Breath")
            .setContentText("High stress detected. Let's do a 4-7-8 breathing cycle: Inhale for 4s, hold 7s, exhale 8s.")
            .setStyle(NotificationCompat.BigTextStyle().bigText(
                "We noticed elevated stress markers while you're offline.\n\n" +
                "• Inhale deeply through your nose for 4 seconds.\n" +
                "• Hold your breath gently for 7 seconds.\n" +
                "• Exhale slowly through your mouth for 8 seconds.\n\n" +
                "You've got this. Your memories will sync to your Council when you reconnect."
            ))
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(8787, notification)
    }
}
