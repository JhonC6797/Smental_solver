"""Solve today's word and publish the run as a static file.

This is what makes the board a site with no server behind it. A scheduled
job runs this a few times a day; the page then loads the recording straight
from the CDN, so a visitor waits for nothing and the Semantle API hears from
this project a handful of times a day rather than once per visitor.

It asks the game a single question before doing any work — does the word we
already recorded still score 100 — so a run that is still current costs one
request and nothing is rewritten.

    python -m scripts.publish_daily
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from semantle.client import SemantleClient
from server.projection import BASIS_FILENAME, BoardProjection
from server.serialization import serialize
from solver import config
from solver.engine import SemantleEngine
from solver.vocabulary import load_vocabulary, Vocabulary

OUTPUT_PATH = config.PROJECT_ROOT / "web" / "public" / "daily.json"
FAILED_RUN_PATH = config.PROJECT_ROOT / "web" / "public" / "daily-failed.json"
SOLVED_SIMILARITY = 100.0


def answer_of(events: list[dict]) -> str | None:
    for event in events:
        if event.get("type") == "solved":
            return event.get("word")
    return None


def read_recording(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def is_current(recording: dict | None, client) -> bool:
    """True if the recorded answer is still today's word."""
    answer = (recording or {}).get("answer")
    if not answer:
        return False
    result = client.get_similarity(answer)
    return result is not None and result.similarity >= SOLVED_SIMILARITY


def build_recording(
    vocabulary: Vocabulary,
    projection: BoardProjection,
    client,
    failed_run_path: Path | None = None,
) -> dict | None:
    """None means the solver never reached the answer this run.

    That is an expected outcome, not an error: the scheduled job tries again
    in a few hours, so the caller must leave the previous recording in place
    rather than fail the workflow. When failed_run_path is given, the run's
    own events are written there — the same wire format as a solved
    recording, so the board can load and replay a failure for diagnosis.
    """
    events = [
        serialize(event, projection)
        for event in SemantleEngine(vocabulary, client).run()
    ]
    answer = answer_of(events)
    if answer is None:
        if failed_run_path is not None:
            _write_recording(failed_run_path, {"answer": None, "events": events})
        return None
    return _stamped({"answer": answer, "events": events})


def _stamped(recording: dict) -> dict:
    return {**recording, "recorded_at": datetime.now(timezone.utc).isoformat()}


def _write_recording(path: Path, recording: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stamped(recording), ensure_ascii=False), encoding="utf-8")


def main() -> None:
    client = SemantleClient()
    existing = read_recording(OUTPUT_PATH)
    if is_current(existing, client):
        print(f"'{existing['answer']}' is still today's word; nothing to publish")
        return

    print("The word has changed. Solving...")
    vocabulary = load_vocabulary()
    projection = BoardProjection(vocabulary, config.VOCAB_DIR / BASIS_FILENAME)
    recording = build_recording(vocabulary, projection, client, FAILED_RUN_PATH)
    if recording is None:
        print(
            "The solver did not reach the answer, so there is nothing worth "
            "publishing. The previous recording is left in place. The failed "
            f"run's events were written to {FAILED_RUN_PATH} for diagnosis."
        )
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(recording, ensure_ascii=False), encoding="utf-8"
    )
    guesses = sum(1 for event in recording["events"] if event["type"] == "guess")
    print(f"Published '{recording['answer']}' in {guesses} guesses to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
