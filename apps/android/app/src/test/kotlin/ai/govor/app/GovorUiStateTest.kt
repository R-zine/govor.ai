package ai.govor.app

import ai.govor.core.SessionState
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class GovorUiStateTest {
    @Test
    fun `connection UI is isolated until media connects`() {
        assertEquals(
            GovorScreen.CONNECTION,
            resolveGovorScreen(mediaConnected = false, lessonActive = false),
        )
        assertEquals(
            GovorScreen.CONNECTION,
            resolveGovorScreen(mediaConnected = false, lessonActive = true),
        )
    }

    @Test
    fun `connected client shows selection only outside an active lesson`() {
        assertEquals(
            GovorScreen.LESSON_SELECTION,
            resolveGovorScreen(mediaConnected = true, lessonActive = false),
        )
        assertEquals(
            GovorScreen.ACTIVE_LESSON,
            resolveGovorScreen(mediaConnected = true, lessonActive = true),
        )
    }

    @Test
    fun `playback actions require an active teacher turn`() {
        assertFalse(
            lessonControlVisibility(SessionState.READY, hasTeacherTurn = false).playbackActions,
        )
        assertTrue(
            lessonControlVisibility(
                SessionState.TEACHER_SPEAKING,
                hasTeacherTurn = true,
            ).playbackActions,
        )
    }

    @Test
    fun `talk and retry are exposed only in their useful lesson states`() {
        assertTrue(
            lessonControlVisibility(
                SessionState.AWAITING_LEARNER,
                hasTeacherTurn = true,
            ).pushToTalk,
        )
        assertTrue(
            lessonControlVisibility(
                SessionState.RECORDING,
                hasTeacherTurn = true,
            ).pushToTalk,
        )
        assertFalse(
            lessonControlVisibility(
                SessionState.PROCESSING,
                hasTeacherTurn = true,
            ).pushToTalk,
        )
        assertTrue(
            lessonControlVisibility(
                SessionState.RECOVERABLE_ERROR,
                hasTeacherTurn = true,
            ).retry,
        )
    }

    @Test
    fun `learner transcript does not survive a lesson boundary`() {
        val state = LessonTransientUiState()

        state.showTranscript("That is all, thank you.")
        assertEquals("That is all, thank you.", state.transcript.value)

        state.endLesson()
        assertNull(state.transcript.value)

        state.showTranscript("A later answer")
        state.beginLesson()
        assertNull(state.transcript.value)
    }

    @Test
    fun `successful host state dismisses a recovered error`() {
        val state = LessonTransientUiState()

        state.showError("The lesson step timed out.")
        state.applyHostState(SessionState.RECOVERABLE_ERROR)
        assertEquals("The lesson step timed out.", state.error.value)

        state.applyHostState(SessionState.PROCESSING)
        assertNull(state.error.value)
    }
}
