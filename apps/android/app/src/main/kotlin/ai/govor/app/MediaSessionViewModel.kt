package ai.govor.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class MediaSessionViewModel(application: Application) : AndroidViewModel(application) {
    val session = WebRtcSession(application.applicationContext)
    val lesson = LessonSessionClient()
    private val credentialStore = SecureGatewayCredentialStore(application.applicationContext)
    private val mutablePairingError = MutableStateFlow<String?>(null)
    val pairingError: StateFlow<String?> = mutablePairingError

    fun connect(
        mediaHost: String,
        controlHost: String,
        pairingToken: String,
        certificateFingerprint: String,
        scenarioId: String,
        englishLocale: String,
        spacedReviewEnabled: Boolean,
    ) {
        if (BuildConfig.DEBUG) {
            session.connect(mediaHost, pairingToken)
            lesson.connect(controlHost, scenarioId, englishLocale, spacedReviewEnabled)
            return
        }
        viewModelScope.launch(Dispatchers.IO) {
            runCatching {
                val normalizedControl = GatewaySecurity.normalizeHost(controlHost)
                val normalizedMedia = GatewaySecurity.normalizeHost(mediaHost)
                val stored = credentialStore.load()?.takeIf {
                    it.controlHost == normalizedControl && it.mediaHost == normalizedMedia &&
                        (certificateFingerprint.isBlank() ||
                            it.certificateFingerprint ==
                            GatewaySecurity.normalizeFingerprint(certificateFingerprint))
                }
                val gateway = stored ?: GatewayPairingClient().pair(
                    normalizedControl,
                    normalizedMedia,
                    pairingToken,
                    certificateFingerprint,
                ).also(credentialStore::save)
                mutablePairingError.value = null
                session.connect(
                    gateway.mediaHost,
                    gateway.credential,
                    secure = true,
                    deviceId = gateway.deviceId,
                    certificateFingerprint = gateway.certificateFingerprint,
                )
                lesson.connect(
                    gateway.controlHost,
                    scenarioId,
                    englishLocale,
                    spacedReviewEnabled,
                    secure = true,
                    deviceId = gateway.deviceId,
                    credential = gateway.credential,
                    certificateFingerprint = gateway.certificateFingerprint,
                )
            }.onFailure { error ->
                mutablePairingError.value = error.message ?: "Pairing failed."
            }
        }
    }

    fun setPushToTalk(active: Boolean) {
        session.setPushToTalk(active)
        if (active) lesson.beginRecording() else lesson.submitRecording()
    }

    fun disconnect() {
        lesson.disconnect()
        session.disconnect()
    }

    override fun onCleared() {
        lesson.release()
        session.release()
    }
}
