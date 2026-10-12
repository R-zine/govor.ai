package ai.govor.app

import ai.govor.core.ControlContractCodec
import ai.govor.core.LearnerTranscriptPayload
import ai.govor.core.MessageEnvelope
import ai.govor.core.RecordingStartedPayload
import ai.govor.core.RecordingSubmittedPayload
import ai.govor.core.PronunciationPayload
import ai.govor.core.SessionCancelPayload
import ai.govor.core.SessionEndedPayload
import ai.govor.core.SessionErrorPayload
import ai.govor.core.SessionStartPayload
import ai.govor.core.SessionState
import ai.govor.core.SessionStatePayload
import ai.govor.core.TeacherPlaybackCompletedPayload
import ai.govor.core.TeacherTurnPayload
import ai.govor.core.TeacherWordAudioPayload
import ai.govor.core.TeacherWordReplayRequestPayload
import ai.govor.core.SpeechTimeline
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.media.PlaybackParams
import android.util.Base64
import android.util.Log
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
import kotlin.math.abs
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
    @Volatile private var activeTrack: AudioTrack? = null
    private var activeTurn: TeacherTurnPayload? = null

    private val mutableState = MutableStateFlow(SessionState.DISCONNECTED)
    val state: StateFlow<SessionState> = mutableState

    private val mutableTeacherText = MutableStateFlow<String?>(null)
    val teacherText: StateFlow<String?> = mutableTeacherText

    private val mutablePronunciations = MutableStateFlow<List<PronunciationPayload>>(emptyList())
    val pronunciations: StateFlow<List<PronunciationPayload>> = mutablePronunciations

    private val mutableHighlightedWordIndex = MutableStateFlow<Int?>(null)
    val highlightedWordIndex: StateFlow<Int?> = mutableHighlightedWordIndex

    private val mutableSelectedPronunciation = MutableStateFlow<PronunciationPayload?>(null)
    val selectedPronunciation: StateFlow<PronunciationPayload?> = mutableSelectedPronunciation

    private val mutablePlaybackRate = MutableStateFlow(1.0f)
    val playbackRate: StateFlow<Float> = mutablePlaybackRate

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

    fun setPlaybackRate(rate: Float) {
        require(rate in SpeechTimeline.supportedRates)
        mutablePlaybackRate.value = rate
        Log.i(LOG_TAG, "playback_rate=$rate")
        activeTrack?.let { track ->
            runCatching { track.playbackParams = playbackParams(rate) }
        }
    }

    fun replayTurn() {
        val turn = activeTurn ?: return
        if (mutableState.value != SessionState.AWAITING_LEARNER) return
        playTeacherTurn(turn, notifyHost = false)
    }

    fun selectWord(wordIndex: Int) {
        val turn = activeTurn ?: return
        val pronunciation = turn.pronunciations.getOrNull(wordIndex) ?: return
        mutableSelectedPronunciation.value = pronunciation
        Log.i(LOG_TAG, "word_selected word_index=$wordIndex")
        val activeSession = sessionId ?: return
        if (mutableState.value != SessionState.AWAITING_LEARNER) return
        send(
            "teacher.word_replay_requested",
            TeacherWordReplayRequestPayload(
                session_id = activeSession,
                turn_id = turn.turn_id,
                word_index = wordIndex,
                playback_rate = mutablePlaybackRate.value,
            ),
        )
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
                "teacher.word_audio" -> playWordAudio(
                    ControlContractCodec.decodePayload<TeacherWordAudioPayload>(envelope),
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

    private fun playTeacherTurn(payload: TeacherTurnPayload, notifyHost: Boolean = true) {
        requireMatchingSession(payload.session_id)
        payload.validate()
        val wav = decodeWav(Base64.decode(payload.audio_base64, Base64.NO_WRAP))
        require(wav.sampleRateHz == payload.sample_rate_hz)
        require(abs(wav.durationUs - payload.duration_us) <= 10_000)
        turnId = payload.turn_id
        activeTurn = payload
        mutableTeacherText.value = payload.text
        mutablePronunciations.value = payload.pronunciations
        mutableSelectedPronunciation.value = null
        mutableState.value = SessionState.TEACHER_SPEAKING
        stopPlayback()
        playbackJob = scope.launch {
            val track = buildAudioTrack(wav)
            activeTrack = track
            Log.i(
                LOG_TAG,
                "teacher_start provider=${payload.provider_id} locale=${payload.locale} " +
                    "duration_us=${payload.duration_us} alignment=${payload.word_alignment != null} " +
                    "fallback=${payload.fallback_used} notify_host=$notifyHost",
            )
            try {
                val written = track.write(wav.pcm, 0, wav.pcm.size)
                require(written == wav.pcm.size) { "Incomplete teacher audio write" }
                track.playbackParams = playbackParams(mutablePlaybackRate.value)
                track.play()
                val totalFrames = wav.pcm.size / 2
                var loggedWord: Int? = null
                while (track.playbackHeadPosition.toLong() < totalFrames) {
                    val mediaTimeUs = track.playbackHeadPosition.toLong() * 1_000_000 / wav.sampleRateHz
                    val highlighted = SpeechTimeline.activeWord(
                        mediaTimeUs,
                        payload.word_alignment,
                    )
                    mutableHighlightedWordIndex.value = highlighted
                    if (highlighted != null && highlighted != loggedWord) {
                        loggedWord = highlighted
                        Log.i(
                            LOG_TAG,
                            "highlight word_index=$highlighted media_time_us=$mediaTimeUs",
                        )
                    }
                    delay(15)
                }
            } finally {
                mutableHighlightedWordIndex.value = null
                runCatching { track.stop() }
                track.release()
                if (activeTrack === track) activeTrack = null
            }
            Log.i(LOG_TAG, "teacher_complete notify_host=$notifyHost")
            if (notifyHost && turnId == payload.turn_id && sessionId == payload.session_id) {
                send(
                    "teacher.playback_completed",
                    TeacherPlaybackCompletedPayload(payload.session_id, payload.turn_id),
                )
            } else if (!notifyHost && turnId == payload.turn_id) {
                mutableState.value = SessionState.AWAITING_LEARNER
            }
        }
    }

    private fun playWordAudio(payload: TeacherWordAudioPayload) {
        requireMatchingSession(payload.session_id)
        val turn = requireNotNull(activeTurn)
        require(payload.turn_id == turn.turn_id)
        require(payload.word_index in turn.pronunciations.indices)
        require(payload.word == turn.pronunciations[payload.word_index].word)
        require(payload.locale in setOf("en-GB", "en-US", "bg-BG"))
        require(payload.provider_id.length in 1..64)
        require(payload.audio_format == "wav")
        require(payload.sample_rate_hz in setOf(16_000, 22_050, 24_000, 48_000))
        require(payload.duration_us in 1..30_000_000)
        require(payload.audio_base64.length in 4..2_000_060)
        val wav = decodeWav(Base64.decode(payload.audio_base64, Base64.NO_WRAP))
        require(wav.sampleRateHz == payload.sample_rate_hz)
        require(abs(wav.durationUs - payload.duration_us) <= 10_000)
        stopPlayback()
        playbackJob = scope.launch {
            val track = buildAudioTrack(wav)
            activeTrack = track
            Log.i(
                LOG_TAG,
                "word_start provider=${payload.provider_id} word_index=${payload.word_index} " +
                    "duration_us=${payload.duration_us} fallback=${payload.fallback_used}",
            )
            try {
                val written = track.write(wav.pcm, 0, wav.pcm.size)
                require(written == wav.pcm.size) { "Incomplete word audio write" }
                track.play()
                val totalFrames = wav.pcm.size / 2
                while (track.playbackHeadPosition.toLong() < totalFrames) delay(15)
            } finally {
                runCatching { track.stop() }
                track.release()
                if (activeTrack === track) activeTrack = null
            }
            Log.i(LOG_TAG, "word_complete word_index=${payload.word_index}")
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
        activeTurn = null
        utteranceId = null
        clearSpeechUi()
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
        activeTurn = null
        utteranceId = null
        clearSpeechUi()
        mutableState.value = SessionState.DISCONNECTED
    }

    private fun stopPlayback() {
        playbackJob?.cancel()
        playbackJob = null
        mutableHighlightedWordIndex.value = null
    }

    private fun clearSpeechUi() {
        mutableTeacherText.value = null
        mutablePronunciations.value = emptyList()
        mutableHighlightedWordIndex.value = null
        mutableSelectedPronunciation.value = null
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

    private data class WavPcm(val sampleRateHz: Int, val pcm: ByteArray) {
        val durationUs: Long = pcm.size.toLong() / 2 * 1_000_000 / sampleRateHz
    }

    private fun decodeWav(bytes: ByteArray): WavPcm {
        require(bytes.size in 44..1_500_044)
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
        require(validFormat && sampleRate in setOf(16_000, 22_050, 24_000, 48_000))
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

    private fun playbackParams(rate: Float): PlaybackParams = PlaybackParams()
        .setSpeed(rate)
        .setPitch(1.0f)

    private companion object {
        const val LOG_TAG = "GovorSpeech"
    }
}
