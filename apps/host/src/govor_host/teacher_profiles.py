"""Validated in-memory teacher selection shared with speech providers."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Literal

TeacherProfileId = Literal["elena", "amira", "daniel"]
VoiceGender = Literal["female", "male"]


@dataclass(frozen=True, slots=True)
class TeacherProfile:
    profile_id: TeacherProfileId
    display_name: str
    voice_gender: VoiceGender


PROFILES: dict[TeacherProfileId, TeacherProfile] = {
    "elena": TeacherProfile("elena", "Elena", "female"),
    "amira": TeacherProfile("amira", "Amira", "female"),
    "daniel": TeacherProfile("daniel", "Daniel", "male"),
}
DEFAULT_TEACHER_PROFILE: TeacherProfileId = "amira"


class TeacherProfileSelection:
    """Thread-safe profile state read from TTS worker threads."""

    def __init__(self, profile_id: TeacherProfileId = DEFAULT_TEACHER_PROFILE) -> None:
        self._lock = Lock()
        self._profile_id = self._validated(profile_id)

    @property
    def profile_id(self) -> TeacherProfileId:
        with self._lock:
            return self._profile_id

    @property
    def profile(self) -> TeacherProfile:
        return PROFILES[self.profile_id]

    def select(self, profile_id: str) -> None:
        selected = self._validated(profile_id)
        with self._lock:
            self._profile_id = selected

    @staticmethod
    def _validated(profile_id: str) -> TeacherProfileId:
        if profile_id not in PROFILES:
            raise ValueError("teacher profile is not allow-listed")
        return profile_id  # type: ignore[return-value]
