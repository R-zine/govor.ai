from uuid import uuid4

import pytest
from govor_domain import InvalidTransition, SessionEvent, SessionMachine, SessionState


def apply(machine: SessionMachine, *events: SessionEvent) -> SessionState:
    for event in events:
        machine.apply(event, uuid4())
    return machine.state


def connected_machine() -> SessionMachine:
    machine = SessionMachine()
    apply(
        machine,
        SessionEvent.DISCOVERY_STARTED,
        SessionEvent.HOST_FOUND,
        SessionEvent.PAIRING_ACCEPTED,
        SessionEvent.CONNECTED,
    )
    return machine


def test_happy_path_enforces_push_to_talk_order() -> None:
    machine = connected_machine()

    state = apply(
        machine,
        SessionEvent.TEACHER_PLAYBACK_STARTED,
        SessionEvent.TEACHER_PLAYBACK_FINISHED,
        SessionEvent.RECORDING_STARTED,
        SessionEvent.RECORDING_SUBMITTED,
        SessionEvent.RESPONSE_READY,
    )

    assert state is SessionState.TEACHER_SPEAKING


def test_recording_is_rejected_while_processing() -> None:
    machine = connected_machine()
    apply(
        machine,
        SessionEvent.TEACHER_PLAYBACK_STARTED,
        SessionEvent.TEACHER_PLAYBACK_FINISHED,
        SessionEvent.RECORDING_STARTED,
        SessionEvent.RECORDING_SUBMITTED,
    )

    with pytest.raises(InvalidTransition, match="recording_started"):
        machine.apply(SessionEvent.RECORDING_STARTED, uuid4())


def test_duplicate_event_is_idempotent() -> None:
    machine = SessionMachine()
    event_id = uuid4()

    first = machine.apply(SessionEvent.DISCOVERY_STARTED, event_id)
    second = machine.apply(SessionEvent.DISCOVERY_STARTED, event_id)

    assert first is SessionState.DISCOVERING
    assert second is SessionState.DISCOVERING


def test_disconnect_and_reconnect_return_to_ready() -> None:
    machine = connected_machine()

    assert machine.apply(SessionEvent.CONNECTION_LOST, uuid4()) is SessionState.RECONNECTING
    assert machine.apply(SessionEvent.RECONNECTED, uuid4()) is SessionState.READY


def test_end_is_available_from_active_state() -> None:
    machine = connected_machine()

    assert machine.apply(SessionEvent.END_REQUESTED, uuid4()) is SessionState.ENDING
    assert machine.apply(SessionEvent.ENDED, uuid4()) is SessionState.DISCONNECTED


@pytest.mark.parametrize(
    ("initial", "event", "expected"),
    [
        (SessionState.DISCONNECTED, SessionEvent.DISCOVERY_STARTED, SessionState.DISCOVERING),
        (SessionState.DISCOVERING, SessionEvent.HOST_FOUND, SessionState.PAIRING),
        (SessionState.PAIRING, SessionEvent.PAIRING_ACCEPTED, SessionState.CONNECTING),
        (SessionState.CONNECTING, SessionEvent.CONNECTED, SessionState.READY),
        (SessionState.READY, SessionEvent.TEACHER_PLAYBACK_STARTED, SessionState.TEACHER_SPEAKING),
        (
            SessionState.TEACHER_SPEAKING,
            SessionEvent.TEACHER_PLAYBACK_FINISHED,
            SessionState.AWAITING_LEARNER,
        ),
        (
            SessionState.AWAITING_LEARNER,
            SessionEvent.RECORDING_STARTED,
            SessionState.RECORDING,
        ),
        (SessionState.RECORDING, SessionEvent.RECORDING_SUBMITTED, SessionState.PROCESSING),
        (SessionState.PROCESSING, SessionEvent.RESPONSE_READY, SessionState.TEACHER_SPEAKING),
        (SessionState.RECONNECTING, SessionEvent.RECONNECTED, SessionState.READY),
        (SessionState.RECOVERABLE_ERROR, SessionEvent.RETRY, SessionState.READY),
        (SessionState.ENDING, SessionEvent.ENDED, SessionState.DISCONNECTED),
    ],
)
def test_every_declared_transition(
    initial: SessionState,
    event: SessionEvent,
    expected: SessionState,
) -> None:
    assert SessionMachine(initial).apply(event, uuid4()) is expected


@pytest.mark.parametrize(
    "event",
    [
        SessionEvent.CONNECTION_LOST,
        SessionEvent.RECOVERABLE_FAILURE,
        SessionEvent.FATAL_FAILURE,
        SessionEvent.END_REQUESTED,
    ],
)
def test_every_global_transition(event: SessionEvent) -> None:
    expected = {
        SessionEvent.CONNECTION_LOST: SessionState.RECONNECTING,
        SessionEvent.RECOVERABLE_FAILURE: SessionState.RECOVERABLE_ERROR,
        SessionEvent.FATAL_FAILURE: SessionState.FATAL_ERROR,
        SessionEvent.END_REQUESTED: SessionState.ENDING,
    }[event]

    assert SessionMachine(SessionState.READY).apply(event, uuid4()) is expected


def test_invalid_transition_does_not_consume_event_id() -> None:
    machine = SessionMachine()
    event_id = uuid4()

    with pytest.raises(InvalidTransition):
        machine.apply(SessionEvent.RECORDING_STARTED, event_id)

    assert machine.apply(SessionEvent.DISCOVERY_STARTED, event_id) is SessionState.DISCOVERING
