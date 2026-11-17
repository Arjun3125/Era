package com.example.eras

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private val PERMISSION_REQ_CODE = 1001

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Create programmatic UI layout (sleek & lightweight)
        val layout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(64, 64, 64, 64)
            setBackgroundColor(android.graphics.Color.parseColor("#121212"))
        }

        val titleText = TextView(this).apply {
            text = "Era Ear Companion"
            textSize = 24f
            setTextColor(android.graphics.Color.WHITE)
            setPadding(0, 0, 0, 32)
        }

        val statusText = TextView(this).apply {
            text = "Status: Ready to connect"
            textSize = 14f
            setTextColor(android.graphics.Color.parseColor("#AAAAAA"))
            setPadding(0, 0, 0, 48)
        }

        val prefs = getSharedPreferences("ears_prefs", Context.MODE_PRIVATE)

        val keyInput = EditText(this).apply {
            hint = "Deepgram API Key"
            setHintTextColor(android.graphics.Color.GRAY)
            setTextColor(android.graphics.Color.WHITE)
            setText(prefs.getString("deepgram_key", ""))
            setPadding(24, 24, 24, 24)
        }

        val ipInput = EditText(this).apply {
            hint = "PC Tailscale IP (e.g. 100.64.0.5)"
            setHintTextColor(android.graphics.Color.GRAY)
            setTextColor(android.graphics.Color.WHITE)
            setText(prefs.getString("tailscale_ip", "100.64.0.1"))
            setPadding(24, 24, 24, 48)
        }

        val startBtn = Button(this).apply {
            text = "Start EARS Capture Service"
            setBackgroundColor(android.graphics.Color.parseColor("#1E88E5"))
            setTextColor(android.graphics.Color.WHITE)
            setOnClickListener {
                if (!checkPermissions()) {
                    requestPermissions()
                    return@setOnClickListener
                }
                val key = keyInput.text.toString().trim()
                val ip = ipInput.text.toString().trim()

                prefs.edit()
                    .putString("deepgram_key", key)
                    .putString("tailscale_ip", ip)
                    .apply()

                val serviceIntent = Intent(this@MainActivity, ForegroundMicService::class.java)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent)
                } else {
                    startService(serviceIntent)
                }
                statusText.text = "Status: LISTENING & STREAMING ($ip)"
                statusText.setTextColor(android.graphics.Color.parseColor("#4CAF50"))
                Toast.makeText(this@MainActivity, "EARS Service Started!", Toast.LENGTH_SHORT).show()
            }
        }

        val stopBtn = Button(this).apply {
            text = "Stop Service"
            setBackgroundColor(android.graphics.Color.parseColor("#E53935"))
            setTextColor(android.graphics.Color.WHITE)
            setOnClickListener {
                val stopIntent = Intent(this@MainActivity, ForegroundMicService::class.java).apply {
                    action = "STOP_CAPTURE"
                }
                startService(stopIntent)
                statusText.text = "Status: STOPPED"
                statusText.setTextColor(android.graphics.Color.parseColor("#E53935"))
                Toast.makeText(this@MainActivity, "EARS Service Stopped", Toast.LENGTH_SHORT).show()
            }
        }

        layout.addView(titleText)
        layout.addView(statusText)
        layout.addView(keyInput)
        layout.addView(ipInput)
        layout.addView(startBtn)
        layout.addView(stopBtn)

        setContentView(layout)
        checkPermissions()
    }

    private fun checkPermissions(): Boolean {
        val audioPerm = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        val notifPerm = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else true
        return audioPerm && notifPerm
    }

    private fun requestPermissions() {
        val perms = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        ActivityCompat.requestPermissions(this, perms.toTypedArray(), PERMISSION_REQ_CODE)
    }
}
