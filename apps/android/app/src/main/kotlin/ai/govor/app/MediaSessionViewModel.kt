package ai.govor.app

import android.app.Application
import android.util.Log
import ai.govor.core.LifecycleReconnectPolicy
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class MediaSessionViewModel(application: Application) : AndroidViewModel(application) {
    val session = WebRtcSession(application.applicationContext)
    val lesson = LessonSessionClient()
    private val credentialStore = SecureGatewayCredentialStore(application.applicationContext)
    private val mutablePairingError = MutableStateFlow<String?>(null)
    val pairingError: StateFlow<String?> = mutablePairingError
    private val reconnectPolicy = LifecycleReconnectPolicy()
    private var connectionJob: Job? = null
    private var networkReconnectJob: Job? = null
    private var lastConnection: ConnectionRequest? = null
    private var lastLesson: LessonSelection? = null

    fun connect(
        mediaHost: String,
        controlHost: String,
        pairingToken: String,
        certificateFingerprint: String,
    ) {
        val request = ConnectionRequest(
            mediaHost = mediaHost,
            controlHost = controlHost,
            pairingToken = pairingToken,
            certificateFingerprint = certificateFingerprint,
        )
        lastConnection = request
        reconnectPolicy.connectionRequested()
        connect(request)
    }

    private fun connect(request: ConnectionRequest) {
        connectionJob?.cancel()
        if (BuildConfig.DEBUG) {
            session.connect(request.mediaHost, request.pairingToken)
            lesson.connect(
                request.controlHost,
                lastLesson?.scenarioId,
                lastLesson?.englishLocale ?: "en-GB",
                lastLesson?.spacedReviewEnabled ?: false,
            )
            return
        }
        connectionJob = viewModelScope.launch(Dispatchers.IO) {
            runCatching {
                val normalizedControl = GatewaySecurity.normalizeHost(request.controlHost)
                val normalizedMedia = GatewaySecurity.normalizeHost(request.mediaHost)
                val stored = credentialStore.load()?.takeIf {
                    it.controlHost == normalizedControl && it.mediaHost == normalizedMedia &&
                        (request.certificateFingerprint.isBlank() ||
                            it.certificateFingerprint ==
                            GatewaySecurity.normalizeFingerprint(request.certificateFingerprint))
                }
                val gateway = stored ?: GatewayPairingClient().pair(
                    normalizedControl,
                    normalizedMedia,
                    request.pairingToken,
                    request.certificateFingerprint,
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
                    lastLesson?.scenarioId,
                    lastLesson?.englishLocale ?: "en-GB",
                    lastLesson?.spacedReviewEnabled ?: false,
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

    fun startLesson(
        scenarioId: String,
        englishLocale: String,
        spacedReviewEnabled: Boolean,
    ) {
        lastLesson = LessonSelection(scenarioId, englishLocale, spacedReviewEnabled)
        lesson.startLesson(scenarioId, englishLocale, spacedReviewEnabled)
    }

    fun enterBackground() {
        if (!reconnectPolicy.enterBackground()) return
        Log.i(LIFECYCLE_LOG_TAG, "background_disconnect")
        networkReconnectJob?.cancel()
        networkReconnectJob = null
        connectionJob?.cancel()
        connectionJob = null
        lesson.disconnect()
        session.disconnect()
    }

    fun enterForeground() {
        if (!reconnectPolicy.enterForeground()) return
        val request = lastConnection ?: return
        Log.i(LIFECYCLE_LOG_TAG, "foreground_reconnect")
        connect(reconnectRequest(request))
    }

    fun networkAvailable() {
        if (!reconnectPolicy.shouldRetryConnection()) return
        if (connectionJob?.isActive == true || networkReconnectJob?.isActive == true) return
        if (
            session.status.value !in setOf(
                MediaConnectionStatus.DISCONNECTED,
                MediaConnectionStatus.FAILED,
            ) && lesson.state.value != ai.govor.core.SessionState.DISCONNECTED
        ) {
            return
        }
        val request = lastConnection ?: return
        networkReconnectJob = viewModelScope.launch {
            delay(NETWORK_RECOVERY_DELAY_MS)
            if (!reconnectPolicy.shouldRetryConnection()) return@launch
            Log.i(LIFECYCLE_LOG_TAG, "network_reconnect")
            connect(reconnectRequest(request))
        }
    }

    fun setPushToTalk(active: Boolean) {
        session.setPushToTalk(active)
        if (active) lesson.beginRecording() else lesson.submitRecording()
    }

    fun disconnect() {
        reconnectPolicy.explicitDisconnect()
        networkReconnectJob?.cancel()
        networkReconnectJob = null
        connectionJob?.cancel()
        connectionJob = null
        lastLesson = null
        lesson.disconnect()
        session.disconnect()
    }

    override fun onCleared() {
        networkReconnectJob?.cancel()
        connectionJob?.cancel()
        lesson.release()
        session.release()
    }

    private fun reconnectRequest(request: ConnectionRequest): ConnectionRequest =
        if (BuildConfig.DEBUG) request else request.copy(pairingToken = "")

    private data class ConnectionRequest(
        val mediaHost: String,
        val controlHost: String,
        val pairingToken: String,
        val certificateFingerprint: String,
    )

    private data class LessonSelection(
        val scenarioId: String,
        val englishLocale: String,
        val spacedReviewEnabled: Boolean,
    )

    companion object {
        private const val LIFECYCLE_LOG_TAG = "govor.lifecycle"
        private const val NETWORK_RECOVERY_DELAY_MS = 1_000L
    }
}
