package ai.govor.app

import ai.govor.core.SessionState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

internal enum class GovorScreen {
    CONNECTION,
    LESSON_SELECTION,
    ACTIVE_LESSON,
}

internal data class LessonControlVisibility(
    val playbackActions: Boolean,
    val pushToTalk: Boolean,
    val retry: Boolean,
)

internal fun resolveGovorScreen(
    mediaConnected: Boolean,
    lessonActive: Boolean,
): GovorScreen = when {
    !mediaConnected -> GovorScreen.CONNECTION
    lessonActive -> GovorScreen.ACTIVE_LESSON
    else -> GovorScreen.LESSON_SELECTION
}

internal fun lessonControlVisibility(
    lessonState: SessionState,
    hasTeacherTurn: Boolean,
): LessonControlVisibility = LessonControlVisibility(
    playbackActions = hasTeacherTurn,
    pushToTalk = lessonState in setOf(
        SessionState.AWAITING_LEARNER,
        SessionState.RECORDING,
    ),
    retry = lessonState == SessionState.RECOVERABLE_ERROR,
)

/** Ephemeral learner-facing values that must not survive a lesson boundary or recovery. */
internal class LessonTransientUiState {
    private val mutableTranscript = MutableStateFlow<String?>(null)
    val transcript: StateFlow<String?> = mutableTranscript

    private val mutableError = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = mutableError

    fun beginLesson() = clear()

    fun endLesson() = clear()

    fun disconnect() = clear()

    fun showTranscript(text: String) {
        mutableTranscript.value = text
    }

    fun showError(message: String) {
        mutableError.value = message
    }

    fun applyHostState(state: SessionState) {
        if (state !in setOf(SessionState.RECOVERABLE_ERROR, SessionState.FATAL_ERROR)) {
            mutableError.value = null
        }
    }

    private fun clear() {
        mutableTranscript.value = null
        mutableError.value = null
    }
}
