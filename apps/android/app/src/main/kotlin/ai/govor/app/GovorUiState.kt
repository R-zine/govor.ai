package ai.govor.app

import ai.govor.core.SessionState

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
