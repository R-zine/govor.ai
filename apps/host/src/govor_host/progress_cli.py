"""Local CLI for viewing, exporting, and deleting structured learner history."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from govor_progress import SQLiteProgressRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("view", "export", "delete", "delete-all"),
        help="Operation to perform on the local structured history.",
    )
    parser.add_argument(
        "--database",
        default="data/progress.sqlite3",
        help="Path to the local progress SQLite database.",
    )
    parser.add_argument("--output", help="JSON output path for export.")
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Required acknowledgement for irreversible history deletion.",
    )
    arguments = parser.parse_args(argv)
    repository = SQLiteProgressRepository(arguments.database)

    if arguments.action == "view":
        print(_json(repository.history()))
        return 0
    if arguments.action == "export":
        if not arguments.output:
            parser.error("export requires --output")
        _write_atomic(Path(arguments.output), _json(repository.history()) + "\n")
        print(f"Exported structured learner history to {arguments.output}")
        return 0
    if not arguments.confirm_delete:
        parser.error(f"{arguments.action} requires --confirm-delete")
    if arguments.action == "delete-all":
        repository.delete_all_learner_data()
        print("Deleted all learner history and restored learner settings to defaults.")
    else:
        repository.delete_history()
        print("Deleted structured learner history; learner settings were preserved.")
    return 0


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
