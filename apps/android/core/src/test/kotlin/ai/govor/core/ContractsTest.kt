package ai.govor.core

import kotlinx.serialization.SerializationException
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.UUID

class ContractsTest {
    @Test
    fun `envelope deserializes with protocol version`() {
        val value = ControlContractCodec.decodeEnvelope(
            """{"protocol_version":"1.0","message_type":"session.start","correlation_id":"9a352221-6fbd-4dd0-9fee-d14a07998d72","payload":{}}""",
        )

        assertEquals(PROTOCOL_VERSION, value.protocol_version)
        assertEquals("session.start", value.message_type)
    }

    @Test
    fun `teacher turn payload deserializes strictly`() {
        val fixture = requireNotNull(
            javaClass.classLoader.getResource("valid/control-teacher-turn.json"),
        ).readText()
        val envelope = ControlContractCodec.decodeEnvelope(fixture)

        val turn = ControlContractCodec.decodePayload<TeacherTurnPayload>(envelope).validate()

        assertEquals("Welcome. What would you like to order?", turn.text)
        assertEquals(150_000, turn.duration_us)
        assertTrue(turn.provider_id.startsWith("fake-"))
        assertEquals("ˈwɛlkəm", turn.pronunciations.first().ipa)
        assertEquals(0, turn.word_alignment?.first()?.word_index)
        assertFalse(turn.fallback_used)
        assertEquals("cafe-ordering", turn.lesson_progress?.scenario_id)
        assertEquals(1, turn.lesson_progress?.exercise_number)
        assertEquals("intermediate", turn.lesson_progress?.difficulty)
    }

    @Test
    fun `lesson catalog payload deserializes strictly`() {
        val fixture = requireNotNull(
            javaClass.classLoader.getResource("valid/control-lesson-catalog.json"),
        ).readText()
        val envelope = ControlContractCodec.decodeEnvelope(fixture)

        val catalog = ControlContractCodec.decodePayload<LessonCatalogPayload>(
            envelope,
        ).validate()

        assertEquals("cafe-ordering", catalog.default_scenario_id)
        assertEquals(
            listOf("cafe-ordering", "airport-travel"),
            catalog.lessons.map { it.scenario_id },
        )
        assertEquals("Ordering at a café", catalog.lessons.first().title)
    }

    @Test
    fun `word replay request and audio fixtures deserialize strictly`() {
        val requestEnvelope = ControlContractCodec.decodeEnvelope(
            requireNotNull(
                javaClass.classLoader.getResource("valid/control-word-replay-request.json"),
            ).readText(),
        )
        val audioEnvelope = ControlContractCodec.decodeEnvelope(
            requireNotNull(
                javaClass.classLoader.getResource("valid/control-word-audio.json"),
            ).readText(),
        )

        val request = ControlContractCodec.decodePayload<TeacherWordReplayRequestPayload>(
            requestEnvelope,
        )
        val audio = ControlContractCodec.decodePayload<TeacherWordAudioPayload>(audioEnvelope)

        assertEquals(0.75f, request.playback_rate)
        assertEquals(request.turn_id, audio.turn_id)
        assertEquals(request.word_index, audio.word_index)
        assertEquals("Welcome", audio.word)
        assertFalse(audio.fallback_used)
    }

    @Test
    fun `invalid completed lesson progress is rejected`() {
        val progress = LessonProgressPayload(
            scenario_id = "cafe-ordering",
            scenario_title = "Ordering at a café",
            exercise_number = 3,
            exercise_count = 3,
            successful_exercises = 2,
            attempts_on_exercise = 0,
            difficulty = "intermediate",
            status = "completed",
            resumed = false,
        )

        assertThrows(IllegalArgumentException::class.java) { progress.validate() }
    }

    @Test
    fun `unknown payload field is rejected`() {
        val envelope = ControlContractCodec.decodeEnvelope(
            """{"protocol_version":"1.0","message_type":"session.state","correlation_id":"42b606a0-d767-4c22-a86f-3354d7186e73","payload":{"session_id":"3191d8bd-d30f-488b-a324-cb91f1286745","state":"ready","event_id":"19c369b5-6fca-43ea-bffc-764b51b7e7c2","unexpected":true}}""",
        )

        assertThrows(SerializationException::class.java) {
            ControlContractCodec.decodePayload<SessionStatePayload>(envelope)
        }
    }

    @Test
    fun `outbound payload uses the common envelope`() {
        val clientId = UUID.randomUUID().toString()
        val correlationId = UUID.randomUUID().toString()

        val encoded = ControlContractCodec.encodeEnvelope(
            "session.start",
            correlationId,
            SessionStartPayload(
                client_id = clientId,
                scenario_id = "airport-travel",
                english_locale = "en-US",
                spaced_review_enabled = true,
            ),
        )
        val decoded = ControlContractCodec.decodeEnvelope(encoded)

        assertEquals(correlationId, decoded.correlation_id)
        val start = ControlContractCodec.decodePayload<SessionStartPayload>(decoded)
        assertEquals(clientId, start.client_id)
        assertEquals("airport-travel", start.scenario_id)
        assertEquals("en-US", start.english_locale)
        assertTrue(start.spaced_review_enabled)
        assertFalse(encoded.contains("unexpected"))
    }

    @Test
    fun `recording cannot overlap processing`() {
        val machine = SessionMachine(SessionState.PROCESSING)

        assertThrows(InvalidTransition::class.java) {
            machine.apply(SessionEvent.RECORDING_STARTED, "new-event")
        }
    }

    @Test
    fun `duplicate event is idempotent`() {
        val machine = SessionMachine()

        assertEquals(SessionState.DISCOVERING, machine.apply(SessionEvent.DISCOVERY_STARTED, "one"))
        assertEquals(SessionState.DISCOVERING, machine.apply(SessionEvent.DISCOVERY_STARTED, "one"))
    }

    @Test
    fun `invalid transition does not consume event identifier`() {
        val machine = SessionMachine()

        assertThrows(InvalidTransition::class.java) {
            machine.apply(SessionEvent.RECORDING_STARTED, "retryable-id")
        }

        assertEquals(
            SessionState.DISCOVERING,
            machine.apply(SessionEvent.DISCOVERY_STARTED, "retryable-id"),
        )
    }

    @Test
    fun `happy path and global transitions match host state machine`() {
        val machine = connectedMachine()

        assertEquals(
            SessionState.TEACHER_SPEAKING,
            machine.apply(SessionEvent.TEACHER_PLAYBACK_STARTED, "speak"),
        )
        assertEquals(
            SessionState.AWAITING_LEARNER,
            machine.apply(SessionEvent.TEACHER_PLAYBACK_FINISHED, "heard"),
        )
        assertEquals(SessionState.RECORDING, machine.apply(SessionEvent.RECORDING_STARTED, "record"))
        assertEquals(
            SessionState.PROCESSING,
            machine.apply(SessionEvent.RECORDING_SUBMITTED, "submit"),
        )
        assertEquals(
            SessionState.RECOVERABLE_ERROR,
            machine.apply(SessionEvent.RECOVERABLE_FAILURE, "failed"),
        )
        assertEquals(SessionState.READY, machine.apply(SessionEvent.RETRY, "retry"))
        assertEquals(
            SessionState.RECONNECTING,
            machine.apply(SessionEvent.CONNECTION_LOST, "lost"),
        )
        assertEquals(SessionState.READY, machine.apply(SessionEvent.RECONNECTED, "back"))
        assertEquals(SessionState.ENDING, machine.apply(SessionEvent.END_REQUESTED, "end"))
        assertEquals(SessionState.FATAL_ERROR, machine.apply(SessionEvent.FATAL_FAILURE, "fatal"))
    }

    @Test
    fun `every declared state transition is covered`() {
        val cases = listOf(
            Triple(SessionState.DISCONNECTED, SessionEvent.DISCOVERY_STARTED, SessionState.DISCOVERING),
            Triple(SessionState.DISCOVERING, SessionEvent.HOST_FOUND, SessionState.PAIRING),
            Triple(SessionState.PAIRING, SessionEvent.PAIRING_ACCEPTED, SessionState.CONNECTING),
            Triple(SessionState.CONNECTING, SessionEvent.CONNECTED, SessionState.READY),
            Triple(SessionState.READY, SessionEvent.TEACHER_PLAYBACK_STARTED, SessionState.TEACHER_SPEAKING),
            Triple(
                SessionState.TEACHER_SPEAKING,
                SessionEvent.TEACHER_PLAYBACK_FINISHED,
                SessionState.AWAITING_LEARNER,
            ),
            Triple(SessionState.AWAITING_LEARNER, SessionEvent.RECORDING_STARTED, SessionState.RECORDING),
            Triple(SessionState.RECORDING, SessionEvent.RECORDING_SUBMITTED, SessionState.PROCESSING),
            Triple(SessionState.PROCESSING, SessionEvent.RESPONSE_READY, SessionState.TEACHER_SPEAKING),
            Triple(SessionState.RECONNECTING, SessionEvent.RECONNECTED, SessionState.READY),
            Triple(SessionState.RECOVERABLE_ERROR, SessionEvent.RETRY, SessionState.READY),
            Triple(SessionState.ENDING, SessionEvent.ENDED, SessionState.DISCONNECTED),
        )

        cases.forEachIndexed { index, (initial, event, expected) ->
            assertEquals(expected, SessionMachine(initial).apply(event, "event-$index"))
        }
    }

    private fun connectedMachine(): SessionMachine = SessionMachine().also { machine ->
        machine.apply(SessionEvent.DISCOVERY_STARTED, "discover")
        machine.apply(SessionEvent.HOST_FOUND, "found")
        machine.apply(SessionEvent.PAIRING_ACCEPTED, "paired")
        machine.apply(SessionEvent.CONNECTED, "connected")
    }
}
