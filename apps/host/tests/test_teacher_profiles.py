from __future__ import annotations

import pytest
from govor_host.teacher_profiles import TeacherProfileSelection


def test_teacher_profile_selection_is_closed_and_reports_gender() -> None:
    selection = TeacherProfileSelection()

    assert selection.profile_id == "amira"
    assert selection.profile.voice_gender == "female"
    selection.select("daniel")
    assert selection.profile.voice_gender == "male"
    with pytest.raises(ValueError, match="allow-listed"):
        selection.select("../../arbitrary")
