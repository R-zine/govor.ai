package ai.govor.app

import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import android.util.Log
import ai.govor.core.LoudspeakerRoutePlatform

@Suppress("DEPRECATION")
internal class AndroidLoudspeakerRoutePlatform(context: Context) : LoudspeakerRoutePlatform {
    private val audioManager = context.getSystemService(AudioManager::class.java)
    private var capturedRoute: CapturedRoute? = null
    private var usedLegacySpeakerphone = false

    override fun captureCurrentRoute() {
        check(capturedRoute == null) { "An audio route is already captured." }
        capturedRoute = CapturedRoute(
            mode = audioManager.mode,
            speakerphoneOn = audioManager.isSpeakerphoneOn,
            communicationDeviceId = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                audioManager.communicationDevice?.id
            } else {
                null
            },
        )
    }

    override fun selectLoudspeaker(): Boolean = try {
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        usedLegacySpeakerphone = false
        val selected = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val speaker = audioManager.availableCommunicationDevices.firstOrNull {
                it.type == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER
            }
            speaker != null && audioManager.setCommunicationDevice(speaker)
        } else {
            false
        }
        if (selected) {
            true
        } else {
            usedLegacySpeakerphone = true
            audioManager.isSpeakerphoneOn = true
            audioManager.isSpeakerphoneOn
        }
    } catch (error: RuntimeException) {
        Log.w(LOG_TAG, "Unable to select the built-in loudspeaker.", error)
        false
    }

    override fun restoreCapturedRoute() {
        val route = capturedRoute ?: return
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val priorDevice = route.communicationDeviceId?.let { deviceId ->
                    audioManager.availableCommunicationDevices.firstOrNull { it.id == deviceId }
                }
                if (priorDevice == null) {
                    audioManager.clearCommunicationDevice()
                } else {
                    audioManager.setCommunicationDevice(priorDevice)
                }
            }
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S || usedLegacySpeakerphone) {
                audioManager.isSpeakerphoneOn = route.speakerphoneOn
            }
            audioManager.mode = route.mode
        } catch (error: RuntimeException) {
            Log.w(LOG_TAG, "Unable to restore the previous audio route.", error)
        } finally {
            capturedRoute = null
            usedLegacySpeakerphone = false
        }
    }

    private data class CapturedRoute(
        val mode: Int,
        val speakerphoneOn: Boolean,
        val communicationDeviceId: Int?,
    )

    private companion object {
        const val LOG_TAG = "GovorAudioRoute"
    }
}
