from __future__ import annotations

import json

import pytest
from govor_host.progress_cli import main
from govor_progress import SQLiteProgressRepository


def test_view_and_export_contain_only_structured_history(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "progress.sqlite3"
    SQLiteProgressRepository(database).load_or_start("cafe-ordering")

    assert main(["view", "--database", str(database)]) == 0
    viewed = json.loads(capsys.readouterr().out)
    assert viewed["scenarios"][0]["scenario_id"] == "cafe-ordering"

    output = tmp_path / "export" / "history.json"
    assert main(["export", "--database", str(database), "--output", str(output)]) == 0
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported == viewed
    assert "transcript" not in output.read_text(encoding="utf-8").casefold()


def test_delete_requires_confirmation_and_preserves_settings(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "progress.sqlite3"
    repository = SQLiteProgressRepository(database)
    repository.load_or_start("airport-travel")

    with pytest.raises(SystemExit):
        main(["delete", "--database", str(database)])
    assert repository.history()["scenarios"]

    assert main(["delete", "--database", str(database), "--confirm-delete"]) == 0
    assert repository.history()["scenarios"] == []
    assert repository.history()["settings"]["english_locale"] == "en-GB"
