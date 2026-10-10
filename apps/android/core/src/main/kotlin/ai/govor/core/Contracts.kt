package ai.govor.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.encodeToJsonElement
import java.util.UUID

const val PROTOCOL_VERSION = "1.0"

@Serializable
data class MessageEnvelope(
    val protocol_version: String,
    val message_type: String,
    val correlation_id: String,
    val payload: JsonObject,
) {
    fun validate(): MessageEnvelope {
        require(protocol_version == PROTOCOL_VERSION) { "Unsupported protocol version" }
        require(message_type.matches(Regex("^[a-z][a-z0-9_.-]{0,63}$"))) {
            "Invalid message type"
        }
        require(UUID.fromString(correlation_id).toString() == correlation_id.lowercase()) {
            "Invalid correlation identifier"
        }
        return this
    }
}

@Serializable
enum class SessionState {
    @SerialName("disconnected")
    DISCONNECTED,

    @SerialName("discovering")
    DISCOVERING,

    @SerialName("pairing")
    PAIRING,

    @SerialName("connecting")
    CONNECTING,

    @SerialName("ready")
    READY,

    @SerialName("teacher_speaking")
    TEACHER_SPEAKING,

    @SerialName("awaiting_learner")
    AWAITING_LEARNER,

    @SerialName("recording")
    RECORDING,

    @SerialName("processing")
    PROCESSING,

    @SerialName("reconnecting")
    RECONNECTING,

    @SerialName("recoverable_error")
    RECOVERABLE_ERROR,

    @SerialName("fatal_error")
    FATAL_ERROR,

    @SerialName("ending")
    ENDING,
}

@Serializable
data class SessionStartPayload(val client_id: String)

@Serializable
data class SessionScopedPayload(val session_id: String)

@Serializable
data class TeacherPlaybackCompletedPayload(val session_id: String, val turn_id: String)

@Serializable
data class RecordingStartedPayload(val session_id: String, val utterance_id: String)

@Serializable
data class RecordingSubmittedPayload(
    val session_id: String,
    val utterance_id: String,
    val duration_us: Long,
    val audio_reference: String = "webrtc",
)

@Serializable
data class SessionCancelPayload(val session_id: String, val reason: String = "user")

@Serializable
data class SessionStatePayload(
    val session_id: String,
    val state: SessionState,
    val event_id: String,
)

@Serializable
data class SessionEndedPayload(val session_id: String, val reason: String)

@Serializable
data class TeacherTurnPayload(
    val session_id: String,
    val turn_id: String,
    val text: String,
    val locale: String,
    val provider_id: String,
    val audio_format: String,
    val sample_rate_hz: Int,
    val duration_us: Long,
    val audio_base64: String,
    val word_alignment: String? = null,
    val phoneme_alignment: String? = null,
)

@Serializable
data class LearnerTranscriptPayload(
    val session_id: String,
    val utterance_id: String,
    val text: String,
    val locale: String,
    val provider_id: String,
)

@Serializable
data class SessionErrorPayload(
    val code: String,
    val message: String,
    val retryable: Boolean,
    val session_id: String? = null,
)

object ControlContractCodec {
    val json = Json {
        ignoreUnknownKeys = false
        isLenient = false
        explicitNulls = true
    }

    fun decodeEnvelope(text: String): MessageEnvelope =
        json.decodeFromString<MessageEnvelope>(text).validate()

    inline fun <reified T> decodePayload(envelope: MessageEnvelope): T =
        json.decodeFromJsonElement<T>(envelope.payload)

    inline fun <reified T> encodeEnvelope(
        messageType: String,
        correlationId: String,
        payload: T,
    ): String {
        UUID.fromString(correlationId)
        val payloadObject = json.encodeToJsonElement(payload) as? JsonObject
            ?: throw IllegalArgumentException("Payload must encode as a JSON object")
        return json.encodeToString(
            MessageEnvelope(
                protocol_version = PROTOCOL_VERSION,
                message_type = messageType,
                correlation_id = correlationId,
                payload = payloadObject,
            ).validate(),
        )
    }
}
