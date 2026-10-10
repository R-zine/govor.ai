"""Deterministic push-to-talk session state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class SessionState(StrEnum):
    DISCONNECTED = "disconnected"
    DISCOVERING = "discovering"
    PAIRING = "pairing"
    CONNECTING = "connecting"
    READY = "ready"
    TEACHER_SPEAKING = "teacher_speaking"
    AWAITING_LEARNER = "awaiting_learner"
    RECORDING = "recording"
    PROCESSING = "processing"
    RECONNECTING = "reconnecting"
    RECOVERABLE_ERROR = "recoverable_error"
    FATAL_ERROR = "fatal_error"
    ENDING = "ending"


class SessionEvent(StrEnum):
    DISCOVERY_STARTED = "discovery_started"
    HOST_FOUND = "host_found"
    PAIRING_ACCEPTED = "pairing_accepted"
    CONNECTED = "connected"
    TEACHER_PLAYBACK_STARTED = "teacher_playback_started"
    TEACHER_PLAYBACK_FINISHED = "teacher_playback_finished"
    RECORDING_STARTED = "recording_started"
    RECORDING_SUBMITTED = "recording_submitted"
    RESPONSE_READY = "response_ready"
    CONNECTION_LOST = "connection_lost"
    RECONNECTED = "reconnected"
    RECOVERABLE_FAILURE = "recoverable_failure"
    RETRY = "retry"
    FATAL_FAILURE = "fatal_failure"
    END_REQUESTED = "end_requested"
    ENDED = "ended"


class InvalidTransition(ValueError):
    """Raised when an event conflicts with the current session state."""


TRANSITIONS: dict[tuple[SessionState, SessionEvent], SessionState] = {
    (SessionState.DISCONNECTED, SessionEvent.DISCOVERY_STARTED): SessionState.DISCOVERING,
    (SessionState.DISCOVERING, SessionEvent.HOST_FOUND): SessionState.PAIRING,
    (SessionState.PAIRING, SessionEvent.PAIRING_ACCEPTED): SessionState.CONNECTING,
    (SessionState.CONNECTING, SessionEvent.CONNECTED): SessionState.READY,
    (SessionState.READY, SessionEvent.TEACHER_PLAYBACK_STARTED): SessionState.TEACHER_SPEAKING,
    (
        SessionState.TEACHER_SPEAKING,
        SessionEvent.TEACHER_PLAYBACK_FINISHED,
    ): SessionState.AWAITING_LEARNER,
    (SessionState.AWAITING_LEARNER, SessionEvent.RECORDING_STARTED): SessionState.RECORDING,
    (SessionState.RECORDING, SessionEvent.RECORDING_SUBMITTED): SessionState.PROCESSING,
    (SessionState.PROCESSING, SessionEvent.RESPONSE_READY): SessionState.TEACHER_SPEAKING,
    (SessionState.RECONNECTING, SessionEvent.RECONNECTED): SessionState.READY,
    (SessionState.RECOVERABLE_ERROR, SessionEvent.RETRY): SessionState.READY,
    (SessionState.ENDING, SessionEvent.ENDED): SessionState.DISCONNECTED,
}

ACTIVE_STATES = frozenset(
    {
        SessionState.CONNECTING,
        SessionState.READY,
        SessionState.TEACHER_SPEAKING,
        SessionState.AWAITING_LEARNER,
        SessionState.RECORDING,
        SessionState.PROCESSING,
        SessionState.RECONNECTING,
        SessionState.RECOVERABLE_ERROR,
    }
)


@dataclass(slots=True)
class SessionMachine:
    """Pure state machine with event idempotency for retried control messages."""

    state: SessionState = SessionState.DISCONNECTED
    _handled_event_ids: set[UUID] = field(default_factory=set, repr=False)

    def apply(self, event: SessionEvent, event_id: UUID) -> SessionState:
        if event_id in self._handled_event_ids:
            return self.state

        next_state = self._next_state(event)
        self.state = next_state
        self._handled_event_ids.add(event_id)
        return next_state

    def _next_state(self, event: SessionEvent) -> SessionState:
        if event is SessionEvent.FATAL_FAILURE and self.state is not SessionState.DISCONNECTED:
            return SessionState.FATAL_ERROR
        if event is SessionEvent.CONNECTION_LOST and self.state in ACTIVE_STATES:
            return SessionState.RECONNECTING
        if event is SessionEvent.RECOVERABLE_FAILURE and self.state in ACTIVE_STATES:
            return SessionState.RECOVERABLE_ERROR
        if event is SessionEvent.END_REQUESTED and self.state not in {
            SessionState.DISCONNECTED,
            SessionState.ENDING,
        }:
            return SessionState.ENDING

        try:
            return TRANSITIONS[(self.state, event)]
        except KeyError as error:
            message = f"Cannot apply {event.value!r} in {self.state.value!r}"
            raise InvalidTransition(message) from error
