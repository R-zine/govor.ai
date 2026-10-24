package ai.govor.app

import ai.govor.core.SessionState
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
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
}
