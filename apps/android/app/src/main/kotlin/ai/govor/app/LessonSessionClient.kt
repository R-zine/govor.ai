package ai.govor.app

import ai.govor.core.ControlContractCodec
import ai.govor.core.LearnerTranscriptPayload
import ai.govor.core.MessageEnvelope
import ai.govor.core.RecordingStartedPayload
import ai.govor.core.RecordingSubmittedPayload
import ai.govor.core.SessionCancelPayload
import ai.govor.core.SessionEndedPayload
import ai.govor.core.SessionErrorPayload
import ai.govor.core.SessionStartPayload
import ai.govor.core.SessionState
import ai.govor.core.SessionStatePayload
import ai.govor.core.TeacherPlaybackCompletedPayload
import ai.govor.core.TeacherTurnPayload
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Base64
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.TimeUnit
import kotlin.math.max

/** Validated Milestone 2 control client. It performs no inference and persists no audio. */
class LessonSessionClient {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var socket: WebSocket? = null
    private var sessionId: String? = null
    private var turnId: String? = null
    private var utteranceId: String? = null
    private var recordingStartedAtNs: Long = 0
    private var playbackJob: Job? = null

    private val mutableState = MutableStateFlow(SessionState.DISCONNECTED)
    val state: StateFlow<SessionState> = mutableState

    private val mutableTeacherText = MutableStateFlow<String?>(null)
    val teacherText: StateFlow<String?> = mutableTeacherText

    private val mutableTranscript = MutableStateFlow<String?>(null)
    val transcript: StateFlow<String?> = mutableTranscript

    private val mutableError = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = mutableError

    fun connect(host: String) {
        closeSocket(notifyHost = false)
        val normalizedHost = host.trim().removePrefix("ws://").removePrefix("wss://").trimEnd('/')
        if (normalizedHost.isBlank()) {
            fail("Enter the Windows control host and port.")
            return
        }
        val request = try {
            Request.Builder().url("ws://$normalizedHost/v1/control").build()
        } catch (_: IllegalArgumentException) {
            fail("Enter a valid Windows control host and port.")
            return
        }
        mutableError.value = null
        mutableState.value = SessionState.CONNECTING
        socket = httpClient.newWebSocket(request, ControlListener())
    }

    fun beginRecording() {
        val activeSession = sessionId ?: return
        if (mutableState.value != SessionState.AWAITING_LEARNER) return
        val nextUtterance = UUID.randomUUID().toString()
        utteranceId = nextUtterance
        recordingStartedAtNs = System.nanoTime()
        mutableState.value = SessionState.RECORDING
        send(
            "learner.recording_started",
            RecordingStartedPayload(activeSession, nextUtterance),
        )
    }

    fun submitRecording() {
        val activeSession = sessionId ?: return
        val activeUtterance = utteranceId ?: return
        if (mutableState.value != SessionState.RECORDING) return
        val durationUs = ((System.nanoTime() - recordingStartedAtNs) / 1_000)
            .coerceIn(1, 30_000_000)
        mutableState.value = SessionState.PROCESSING
        send(
            "learner.recording_submitted",
            RecordingSubmittedPayload(
                session_id = activeSession,
                utterance_id = activeUtterance,
                duration_us = durationUs,
            ),
        )
    }

    fun retry() {
        val activeSession = sessionId ?: return
        if (mutableState.value != SessionState.RECOVERABLE_ERROR) return
        send("session.retry", ai.govor.core.SessionScopedPayload(activeSession))
    }

    fun disconnect() {
        closeSocket(notifyHost = true)
    }

    fun release() {
        closeSocket(notifyHost = true)
        scope.cancel()
        httpClient.dispatcher.executorService.shutdown()
        httpClient.connectionPool.evictAll()
    }

    private fun handleMessage(text: String) {
        runCatching {
            val envelope = ControlContractCodec.decodeEnvelope(text)
            when (envelope.message_type) {
                "session.state" -> applyState(
                    ControlContractCodec.decodePayload<SessionStatePayload>(envelope),
                )
                "teacher.turn" -> playTeacherTurn(
                    ControlContractCodec.decodePayload<TeacherTurnPayload>(envelope),
                )
                "learner.transcript" -> applyTranscript(
                    ControlContractCodec.decodePayload<LearnerTranscriptPayload>(envelope),
                )
                "session.ended" -> applyEnded(
                    ControlContractCodec.decodePayload<SessionEndedPayload>(envelope),
                )
                "error" -> applyError(
                    ControlContractCodec.decodePayload<SessionErrorPayload>(envelope),
                )
                else -> throw IllegalArgumentException("Unsupported host control message")
            }
        }.onFailure {
            fail("Invalid control response from the Windows host.")
        }
    }

    private fun applyState(payload: SessionStatePayload) {
        requireMatchingSession(payload.session_id, allowInitial = true)
        UUID.fromString(payload.event_id)
        mutableState.value = payload.state
    }

    private fun playTeacherTurn(payload: TeacherTurnPayload) {
        requireMatchingSession(payload.session_id)
        require(payload.audio_format == "wav")
        require(payload.duration_us in 1..30_000_000)
        val wav = decodeWav(Base64.decode(payload.audio_base64, Base64.NO_WRAP))
        require(wav.sampleRateHz == payload.sample_rate_hz)
        turnId = payload.turn_id
        mutableTeacherText.value = payload.text
        mutableState.value = SessionState.TEACHER_SPEAKING
        stopPlayback()
        playbackJob = scope.launch {
            val track = buildAudioTrack(wav)
            try {
                val written = track.write(wav.pcm, 0, wav.pcm.size)
                require(written == wav.pcm.size) { "Incomplete teacher audio write" }
                track.play()
                delay(max(1, payload.duration_us / 1_000))
            } finally {
                runCatching { track.stop() }
                track.release()
            }
            if (turnId == payload.turn_id && sessionId == payload.session_id) {
                send(
                    "teacher.playback_completed",
                    TeacherPlaybackCompletedPayload(payload.session_id, payload.turn_id),
                )
            }
        }
    }

    private fun applyTranscript(payload: LearnerTranscriptPayload) {
        requireMatchingSession(payload.session_id)
        require(payload.utterance_id == utteranceId)
        mutableTranscript.value = payload.text
    }

    private fun applyEnded(payload: SessionEndedPayload) {
        requireMatchingSession(payload.session_id)
        stopPlayback()
        sessionId = null
        turnId = null
        utteranceId = null
        mutableState.value = SessionState.DISCONNECTED
    }

    private fun applyError(payload: SessionErrorPayload) {
        payload.session_id?.let { requireMatchingSession(it, allowInitial = true) }
        mutableError.value = payload.message
        if (payload.retryable) mutableState.value = SessionState.RECOVERABLE_ERROR
    }

    private fun requireMatchingSession(value: String, allowInitial: Boolean = false) {
        UUID.fromString(value)
        val active = sessionId
        if (active == null && allowInitial) {
            sessionId = value
        } else {
            require(active == value) { "Control response belongs to another session" }
        }
    }

    private inline fun <reified T> send(messageType: String, payload: T) {
        socket?.send(
            ControlContractCodec.encodeEnvelope(
                messageType,
                UUID.randomUUID().toString(),
                payload,
            ),
        )
    }

    private fun closeSocket(notifyHost: Boolean) {
        val activeSession = sessionId
        if (notifyHost && activeSession != null) {
            send("session.cancel", SessionCancelPayload(activeSession))
        }
        stopPlayback()
        socket?.close(1000, "client disconnect")
        socket = null
        sessionId = null
        turnId = null
        utteranceId = null
        mutableState.value = SessionState.DISCONNECTED
    }

    private fun stopPlayback() {
        playbackJob?.cancel()
        playbackJob = null
    }

    private fun fail(message: String) {
        mutableError.value = message
        mutableState.value = SessionState.RECOVERABLE_ERROR
    }

    private inner class ControlListener : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            if (socket !== webSocket) return
            webSocket.send(
                ControlContractCodec.encodeEnvelope(
                    "session.start",
                    UUID.randomUUID().toString(),
                    SessionStartPayload(UUID.randomUUID().toString()),
                ),
            )
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            if (socket === webSocket) handleMessage(text)
        }

        override fun onFailure(webSocket: WebSocket, throwable: Throwable, response: Response?) {
            if (socket === webSocket) fail("Control connection failed.")
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            if (socket === webSocket && mutableState.value != SessionState.RECOVERABLE_ERROR) {
                mutableState.value = SessionState.DISCONNECTED
            }
        }
    }

    private data class WavPcm(val sampleRateHz: Int, val pcm: ByteArray)

    private fun decodeWav(bytes: ByteArray): WavPcm {
        require(bytes.size in 44..1_048_576)
        require(String(bytes, 0, 4, Charsets.US_ASCII) == "RIFF")
        require(String(bytes, 8, 4, Charsets.US_ASCII) == "WAVE")
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        var offset = 12
        var sampleRate = 0
        var validFormat = false
        var pcm: ByteArray? = null
        while (offset + 8 <= bytes.size) {
            val id = String(bytes, offset, 4, Charsets.US_ASCII)
            val size = buffer.getInt(offset + 4)
            require(size >= 0 && offset + 8L + size <= bytes.size)
            if (id == "fmt " && size >= 16) {
                validFormat = buffer.getShort(offset + 8).toInt() == 1 &&
                    buffer.getShort(offset + 10).toInt() == 1 &&
                    buffer.getShort(offset + 22).toInt() == 16
                sampleRate = buffer.getInt(offset + 12)
            } else if (id == "data") {
                pcm = bytes.copyOfRange(offset + 8, offset + 8 + size)
            }
            offset += 8 + size + (size and 1)
        }
        require(validFormat && sampleRate in setOf(16_000, 24_000, 48_000))
        val decoded = requireNotNull(pcm)
        require(decoded.isNotEmpty() && decoded.size % 2 == 0)
        return WavPcm(sampleRate, decoded)
    }

    private fun buildAudioTrack(wav: WavPcm): AudioTrack {
        val minimum = AudioTrack.getMinBufferSize(
            wav.sampleRateHz,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        return AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build(),
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(wav.sampleRateHz)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build(),
            )
            .setBufferSizeInBytes(max(minimum, wav.pcm.size))
            .setTransferMode(AudioTrack.MODE_STATIC)
            .build()
    }
}
