/*
 * ears_mobile_reference/ForegroundMicService.kt
 *
 * PRODUCTION-READY REFERENCE IMPLEMENTATION
 *
 * How to build your APK:
 * 1. Open Android Studio -> New Project -> Empty Activity (Kotlin, Min SDK 26+).
 * 2. Add dependencies to your app's build.gradle.kts:
 *      implementation("com.squareup.okhttp3:okhttp:4.12.0")
 *      implementation("com.google.code.gson:gson:2.10.1")
 *      implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
 * 3. Paste this file into your project under your package name.
 * 4. Replace DEEPGRAM_API_KEY with your Deepgram key and TAILSCALE_PC_IP with your PC's Tailscale IP.
 * 5. Click Build -> Build Bundle(s) / APK(s) -> Build APK!
 */

package com.example.eras

import android.app.*
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.gson.Gson
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okio.ByteString
import org.json.JSONObject
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.TimeUnit

class ForegroundMicService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var audioRecord: AudioRecord? = null
    private var webSocket: WebSocket? = null
    private var isRunning = false

    // CONFIGURATION (Replace with your actual keys & Tailscale IP)
    private val deepgramApiKey = "YOUR_DEEPGRAM_API_KEY"
    private val tailscaleBackendUrl = "http://YOUR_TAILSCALE_IP:8787/ingest" // e.g., http://100.64.0.5:8787/ingest
    private val deviceId = "android_mobile_client"

    // Offline retry queue for when mobile data or Tailscale is temporarily disconnected
    private val offlineQueue = ConcurrentLinkedQueue<Map<String, Any>>()
    private val gson = Gson()
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundWithNotification("Era is listening", "Ambient memory capture active.")
        if (!isRunning) {
            isRunning = true
            scope.launch { startCaptureAndStreaming() }
            scope.launch { startRetryQueueProcessor() }
        }
        return START_STICKY
    }

    private fun startForegroundWithNotification(title: String, text: String) {
        val channelId = "ears_capture_channel"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId, "Ambient Memory Capture", NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }

        val stopIntent = Intent(this, ForegroundMicService::class.java).apply { action = "STOP_CAPTURE" }
        val pendingStop = PendingIntent.getService(this, 0, stopIntent, PendingIntent.FLAG_IMMUTABLE)

        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_media_pause, "Stop", pendingStop)
            .build()

        startForeground(1, notification)
    }

    private suspend fun startCaptureAndStreaming() {
        val sampleRate = 16000
        val channelConfig = AudioFormat.CHANNEL_IN_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat) * 2

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC, sampleRate, channelConfig, audioFormat, bufferSize
            )

            // Connect to Deepgram WebSocket (multi-language: Hindi, Marathi, English, Hinglish)
            val request = Request.Builder()
                .url("wss://api.deepgram.com/v1/listen?model=nova-2&language=multi&diarize=true&filler_words=true")
                .addHeader("Authorization", "Token $deepgramApiKey")
                .build()

            val currentBatch = mutableListOf<Map<String, Any>>()

            webSocket = httpClient.newWebSocket(request, object : WebSocketListener() {
                override fun onMessage(webSocket: WebSocket, text: String) {
                    try {
                        val json = JSONObject(text)
                        val channel = json.optJSONObject("channel") ?: return
                        val alternatives = channel.optJSONArray("alternatives") ?: return
                        if (alternatives.length() == 0) return

                        val firstAlt = alternatives.getJSONObject(0)
                        val transcript = firstAlt.optString("transcript", "").trim()
                        if (transcript.isEmpty()) return

                        val words = firstAlt.optJSONArray("words")
                        var speaker = "0"
                        var start = 0.0
                        var end = 0.0

                        if (words != null && words.length() > 0) {
                            val firstWord = words.getJSONObject(0)
                            val lastWord = words.getJSONObject(words.length() - 1)
                            speaker = firstWord.optInt("speaker", 0).toString()
                            start = firstWord.optDouble("start", 0.0)
                            end = lastWord.optDouble("end", 0.0)
                        }

                        val segment = mapOf("speaker" to speaker, "text" to transcript, "start" to start, "end" to end)
                        synchronized(currentBatch) {
                            currentBatch.add(segment)
                            if (currentBatch.size >= 5) { // Flush batch every 5 segments
                                postBatchToBackend(deviceId, ArrayList(currentBatch))
                                currentBatch.clear()
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("EARS_Service", "Error parsing Deepgram transcript: ${e.message}")
                    }
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    Log.e("EARS_Service", "WebSocket failed: ${t.message}. Reconnecting in 5s...")
                    scope.launch { delay(5000); if (isRunning) startCaptureAndStreaming() }
                }
            })

            audioRecord?.startRecording()
            val buffer = ByteArray(bufferSize)

            while (isRunning && audioRecord?.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (read > 0) {
                    webSocket?.send(ByteString.of(*buffer.copyOfRange(0, read)))
                }
            }
        } catch (e: Exception) {
            Log.e("EARS_Service", "Audio capture error: ${e.message}")
        }
    }

    private fun postBatchToBackend(deviceId: String, segments: List<Map<String, Any>>) {
        val payload = mapOf("device_id" to deviceId, "segments" to segments)
        val jsonBody = gson.toJson(payload)
        val body = jsonBody.toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder().url(tailscaleBackendUrl).post(body).build()

        httpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: java.io.IOException) {
                Log.w("EARS_Service", "Backend offline or unreachable. Queuing batch offline.")
                offlineQueue.add(payload)
            }

            override fun onResponse(call: Call, response: Response) {
                if (!response.isSuccessful) {
                    Log.w("EARS_Service", "Backend returned HTTP ${response.code}. Queuing offline.")
                    offlineQueue.add(payload)
                } else {
                    Log.i("EARS_Service", "Batch successfully ingested by Era backend!")
                }
                response.close()
            }
        })
    }

    private suspend fun startRetryQueueProcessor() {
        while (isRunning) {
            delay(15000) // Check offline queue every 15 seconds
            while (!offlineQueue.isEmpty() && isRunning) {
                val payload = offlineQueue.peek() ?: break
                val jsonBody = gson.toJson(payload)
                val body = jsonBody.toRequestBody("application/json; charset=utf-8".toMediaType())
                val request = Request.Builder().url(tailscaleBackendUrl).post(body).build()

                try {
                    val response = httpClient.newCall(request).execute()
                    if (response.isSuccessful) {
                        offlineQueue.poll() // Remove from queue on success
                        Log.i("EARS_Service", "Offline queued batch successfully delivered!")
                    }
                    response.close()
                } catch (e: Exception) {
                    break // Stop trying until next cycle if still offline
                }
            }
        }
    }

    fun stopCapture() {
        isRunning = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
            webSocket?.close(1000, "User stopped recording")
        } catch (e: Exception) {
            Log.e("EARS_Service", "Error closing capture: ${e.message}")
        }
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        stopCapture()
        scope.cancel()
        super.onDestroy()
    }
}
