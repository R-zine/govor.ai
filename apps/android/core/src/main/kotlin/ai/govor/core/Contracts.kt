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
data class PairingBootstrapPayload(
    val control_host: String,
    val media_host: String,
    val pairing_code: String,
    val certificate_sha256: String,
    val expires_at_unix: Long,
) {
    fun validate(nowUnixSeconds: Long): PairingBootstrapPayload {
        requireHostPort(control_host)
        requireHostPort(media_host)
        require(pairing_code.matches(Regex("^[0-9]{8}$"))) { "Invalid pairing code" }
        require(certificate_sha256.matches(Regex("^[0-9A-F]{64}$"))) {
            "Invalid certificate fingerprint"
        }
        require(expires_at_unix in 1..4_102_444_800L) { "Invalid pairing expiry" }
        require(expires_at_unix >= nowUnixSeconds) { "The pairing QR has expired" }
        return this
    }

    private fun requireHostPort(value: String) {
        require(value.length <= 259) { "Gateway address is too long" }
        val separator = value.lastIndexOf(':')
        require(separator in 1 until value.lastIndex) { "Invalid gateway address" }
        val host = value.substring(0, separator)
        val port = value.substring(separator + 1)
        require(host.matches(Regex("^[A-Za-z0-9.-]{1,253}$"))) { "Invalid gateway host" }
        val parsedPort = port.toIntOrNull()
        require(port.all(Char::isDigit) && parsedPort != null && parsedPort in 1..65_535) {
            "Invalid gateway port"
        }
    }
}

object PairingBootstrapCodec {
    fun decode(text: String, nowUnixSeconds: Long): PairingBootstrapPayload {
        require(text.toByteArray(Charsets.UTF_8).size <= 2_048) {
            "Pairing QR payload is too large"
        }
        val envelope = ControlContractCodec.decodeEnvelope(text)
        require(envelope.message_type == "pairing.bootstrap") { "Unsupported QR message" }
        return ControlContractCodec.decodePayload<PairingBootstrapPayload>(envelope)
            .validate(nowUnixSeconds)
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
data class SessionStartPayload(
    val client_id: String,
    val scenario_id: String = "cafe-ordering",
    val english_locale: String = "en-GB",
    val spaced_review_enabled: Boolean = false,
)

@Serializable
class LessonCatalogRequestPayload

@Serializable
data class LessonCreateRequestPayload(
    val topic: String,
    val difficulty: String? = null,
    val environment_id: String? = null,
    val exercise_count: Int? = null,
) {
    fun validate(): LessonCreateRequestPayload {
        require(topic.isNotBlank() && topic.length <= 500)
        require(difficulty == null || difficulty in setOf("beginner", "intermediate", "advanced"))
        require(
            environment_id == null ||
                environment_id.matches(Regex("^[a-z][a-z0-9-]{2,63}$")),
        )
        require(exercise_count == null || exercise_count in 1..8)
        return this
    }
}

@Serializable
data class LessonCreateResultPayload(
    val status: String,
    val message: String,
    val scenario_id: String? = null,
    val title: String? = null,
    val difficulty: String? = null,
    val environment_id: String? = null,
    val exercise_count: Int? = null,
) {
    fun validate(): LessonCreateResultPayload {
        require(status in setOf("created", "failed"))
        require(message.isNotBlank() && message.length <= 512)
        val details = listOf(scenario_id, title, difficulty, environment_id, exercise_count)
        require(if (status == "created") details.none { it == null } else details.all { it == null })
        if (status == "created") {
            require(scenario_id!!.matches(Regex("^[a-z][a-z0-9-]{2,63}$")))
            require(title!!.isNotBlank() && title.length <= 128)
            require(difficulty in setOf("beginner", "intermediate", "advanced"))
            require(environment_id!!.matches(Regex("^[a-z][a-z0-9-]{2,63}$")))
            require(exercise_count in 1..8)
        }
        return this
    }
}

@Serializable
data class LessonCreationStatusPayload(
    val job_id: String? = null,
    val state: String,
    val message: String,
    val result: LessonCreateResultPayload? = null,
) {
    fun validate(): LessonCreationStatusPayload {
        require(state in setOf("idle", "generating", "created", "failed"))
        require(message.isNotBlank() && message.length <= 512)
        require((state == "idle") == (job_id == null))
        job_id?.let { java.util.UUID.fromString(it) }
        if (state in setOf("created", "failed")) {
            require(result != null && result.status == state)
            result.validate()
        } else {
            require(result == null)
        }
        return this
    }
}

@Serializable
data class LessonCatalogProgressPayload(
    val status: String,
    val successful_exercises: Int,
    val exercise_count: Int,
    val completed_count: Int,
) {
    fun validate(): LessonCatalogProgressPayload {
        require(status in setOf("not_started", "in_progress", "completed"))
        require(exercise_count in 1..64)
        require(successful_exercises in 0..exercise_count)
        require(completed_count in 0..1_000_000)
        require(status != "not_started" || (successful_exercises == 0 && completed_count == 0))
        require(
            status != "completed" ||
                (successful_exercises == exercise_count && completed_count >= 1),
        )
        return this
    }
}

@Serializable
data class LessonCatalogItemPayload(
    val scenario_id: String,
    val title: String,
    val description: String,
    val display_order: Int,
    val progress: LessonCatalogProgressPayload,
) {
    fun validate(): LessonCatalogItemPayload {
        require(scenario_id.matches(Regex("^[a-z][a-z0-9-]{2,63}$")))
        require(title.isNotBlank() && title.length <= 128)
        require(description.isNotBlank() && description.length <= 512)
        require(display_order in 0..9_999)
        progress.validate()
        return this
    }
}

@Serializable
data class LessonEnvironmentItemPayload(
    val environment_id: String,
    val display_name: String,
) {
    fun validate(): LessonEnvironmentItemPayload {
        require(environment_id.matches(Regex("^[a-z][a-z0-9-]{2,63}$")))
        require(display_name.isNotBlank() && display_name.length <= 128)
        return this
    }
}

@Serializable
data class TeacherProfileItemPayload(
    val profile_id: String,
    val display_name: String,
    val voice_gender: String,
) {
    fun validate(): TeacherProfileItemPayload {
        require(profile_id in setOf("elena", "amira", "daniel"))
        require(display_name.isNotBlank() && display_name.length <= 64)
        require(voice_gender in setOf("female", "male"))
        return this
    }
}

@Serializable
data class TeacherProfileSelectPayload(val profile_id: String)

@Serializable
data class LessonCatalogPayload(
    val default_scenario_id: String,
    val lessons: List<LessonCatalogItemPayload>,
    val environments: List<LessonEnvironmentItemPayload>,
    val teacher_profiles: List<TeacherProfileItemPayload>,
    val selected_teacher_profile_id: String,
) {
    fun validate(): LessonCatalogPayload {
        require(lessons.size in 1..64)
        lessons.forEach { it.validate() }
        require(lessons.map { it.scenario_id }.distinct().size == lessons.size)
        require(default_scenario_id in lessons.map { it.scenario_id })
        require(environments.size in 1..64)
        environments.forEach { it.validate() }
        require(environments.map { it.environment_id }.distinct().size == environments.size)
        require(teacher_profiles.size in 1..8)
        teacher_profiles.forEach { it.validate() }
        require(teacher_profiles.map { it.profile_id }.distinct().size == teacher_profiles.size)
        require(selected_teacher_profile_id in teacher_profiles.map { it.profile_id })
        require(
            lessons == lessons.sortedWith(
                compareBy<LessonCatalogItemPayload> { it.display_order }
                    .thenBy { it.title }
                    .thenBy { it.scenario_id },
            ),
        )
        return this
    }
}

@Serializable
data class SessionScopedPayload(val session_id: String)

@Serializable
data class LessonDeleteRequestPayload(val session_id: String)

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
data class PronunciationPayload(
    val word: String,
    val start_char: Int,
    val end_char: Int,
    val ipa: String,
    val locale: String,
    val explanation: String? = null,
)

@Serializable
data class WordAlignmentPayload(
    val word_index: Int,
    val start_us: Long,
    val end_us: Long,
)

@Serializable
data class PhonemeAlignmentPayload(
    val word_index: Int,
    val symbol: String,
    val start_us: Long,
    val end_us: Long,
)

@Serializable
data class LessonProgressPayload(
    val scenario_id: String,
    val scenario_title: String,
    val exercise_number: Int,
    val exercise_count: Int,
    val successful_exercises: Int,
    val attempts_on_exercise: Int,
    val difficulty: String,
    val status: String,
    val resumed: Boolean,
    val difficulty_change_reason: String? = null,
) {
    fun validate(): LessonProgressPayload {
        require(scenario_id.matches(Regex("^[a-z][a-z0-9-]{2,63}$")))
        require(scenario_title.length in 1..128)
        require(exercise_number in 1..exercise_count && exercise_count in 1..64)
        require(successful_exercises in 0..exercise_count)
        require(attempts_on_exercise in 0..100)
        require(difficulty in setOf("beginner", "intermediate", "advanced"))
        require(status in setOf("in_progress", "completed"))
        require(
            difficulty_change_reason == null ||
                difficulty_change_reason in setOf(
                    "repeated_difficulty",
                    "consistent_first_try_success",
                ),
        )
        require(status != "completed" || successful_exercises == exercise_count)
        return this
    }
}

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
    val pronunciations: List<PronunciationPayload>,
    val word_alignment: List<WordAlignmentPayload>? = null,
    val phoneme_alignment: List<PhonemeAlignmentPayload>? = null,
    val fallback_used: Boolean,
    val lesson_progress: LessonProgressPayload? = null,
) {
    fun validate(): TeacherTurnPayload {
        UUID.fromString(session_id)
        UUID.fromString(turn_id)
        require(text.length in 1..2_048 && text.isNotBlank())
        require(locale in setOf("en-GB", "en-US", "bg-BG"))
        require(provider_id.length in 1..64)
        require(audio_format == "wav")
        require(sample_rate_hz in setOf(16_000, 22_050, 24_000, 48_000))
        require(duration_us in 1..30_000_000)
        require(audio_base64.length in 4..2_000_060)
        require(pronunciations.size <= 256)
        require(word_alignment == null || word_alignment.size <= 256)
        require(phoneme_alignment == null || phoneme_alignment.size <= 2_048)
        pronunciations.forEach { pronunciation ->
            require(pronunciation.start_char >= 0 && pronunciation.end_char <= text.length)
            require(pronunciation.end_char > pronunciation.start_char)
            require(text.substring(pronunciation.start_char, pronunciation.end_char) == pronunciation.word)
            require(pronunciation.ipa.isNotBlank() && pronunciation.locale == locale)
        }
        word_alignment.orEmpty().forEach { alignment ->
            require(alignment.word_index in pronunciations.indices)
            require(alignment.start_us >= 0 && alignment.end_us in 1..duration_us)
            require(alignment.end_us > alignment.start_us)
        }
        phoneme_alignment.orEmpty().forEach { alignment ->
            require(alignment.word_index in pronunciations.indices)
            require(alignment.start_us >= 0 && alignment.end_us in 1..duration_us)
            require(alignment.end_us > alignment.start_us)
        }
        lesson_progress?.validate()
        return this
    }
}

@Serializable
data class TeacherWordReplayRequestPayload(
    val session_id: String,
    val turn_id: String,
    val word_index: Int,
    val playback_rate: Float,
)

@Serializable
data class TeacherWordAudioPayload(
    val session_id: String,
    val turn_id: String,
    val word_index: Int,
    val word: String,
    val locale: String,
    val provider_id: String,
    val audio_format: String,
    val sample_rate_hz: Int,
    val duration_us: Long,
    val audio_base64: String,
    val fallback_used: Boolean,
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
