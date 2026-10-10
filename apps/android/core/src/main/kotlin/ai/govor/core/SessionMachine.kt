package ai.govor.core

enum class SessionEvent {
    DISCOVERY_STARTED,
    HOST_FOUND,
    PAIRING_ACCEPTED,
    CONNECTED,
    TEACHER_PLAYBACK_STARTED,
    TEACHER_PLAYBACK_FINISHED,
    RECORDING_STARTED,
    RECORDING_SUBMITTED,
    RESPONSE_READY,
    CONNECTION_LOST,
    RECONNECTED,
    RECOVERABLE_FAILURE,
    RETRY,
    FATAL_FAILURE,
    END_REQUESTED,
    ENDED,
}

class InvalidTransition(message: String) : IllegalStateException(message)

class SessionMachine(initialState: SessionState = SessionState.DISCONNECTED) {
    var state: SessionState = initialState
        private set

    private val handledEventIds = mutableSetOf<String>()

    fun apply(event: SessionEvent, eventId: String): SessionState {
        if (eventId in handledEventIds) return state
        val next = nextState(event)
        handledEventIds.add(eventId)
        state = next
        return state
    }

    private fun nextState(event: SessionEvent): SessionState {
        if (event == SessionEvent.FATAL_FAILURE && state != SessionState.DISCONNECTED) {
            return SessionState.FATAL_ERROR
        }
        if (event == SessionEvent.CONNECTION_LOST && state in activeStates) {
            return SessionState.RECONNECTING
        }
        if (event == SessionEvent.RECOVERABLE_FAILURE && state in activeStates) {
            return SessionState.RECOVERABLE_ERROR
        }
        if (event == SessionEvent.END_REQUESTED && state !in setOf(SessionState.DISCONNECTED, SessionState.ENDING)) {
            return SessionState.ENDING
        }
        return transitions[state to event]
            ?: throw InvalidTransition("Cannot apply $event in $state")
    }

    private companion object {
        val transitions = mapOf(
            (SessionState.DISCONNECTED to SessionEvent.DISCOVERY_STARTED) to SessionState.DISCOVERING,
            (SessionState.DISCOVERING to SessionEvent.HOST_FOUND) to SessionState.PAIRING,
            (SessionState.PAIRING to SessionEvent.PAIRING_ACCEPTED) to SessionState.CONNECTING,
            (SessionState.CONNECTING to SessionEvent.CONNECTED) to SessionState.READY,
            (SessionState.READY to SessionEvent.TEACHER_PLAYBACK_STARTED) to SessionState.TEACHER_SPEAKING,
            (SessionState.TEACHER_SPEAKING to SessionEvent.TEACHER_PLAYBACK_FINISHED) to SessionState.AWAITING_LEARNER,
            (SessionState.AWAITING_LEARNER to SessionEvent.RECORDING_STARTED) to SessionState.RECORDING,
            (SessionState.RECORDING to SessionEvent.RECORDING_SUBMITTED) to SessionState.PROCESSING,
            (SessionState.PROCESSING to SessionEvent.RESPONSE_READY) to SessionState.TEACHER_SPEAKING,
            (SessionState.RECONNECTING to SessionEvent.RECONNECTED) to SessionState.READY,
            (SessionState.RECOVERABLE_ERROR to SessionEvent.RETRY) to SessionState.READY,
            (SessionState.ENDING to SessionEvent.ENDED) to SessionState.DISCONNECTED,
        )

        val activeStates = setOf(
            SessionState.CONNECTING,
            SessionState.READY,
            SessionState.TEACHER_SPEAKING,
            SessionState.AWAITING_LEARNER,
            SessionState.RECORDING,
            SessionState.PROCESSING,
            SessionState.RECONNECTING,
            SessionState.RECOVERABLE_ERROR,
        )
    }
}
