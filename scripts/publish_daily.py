"""Solve today's word and publish the run as a static file.

This is what makes the board a site with no server behind it. A scheduled
job runs this a few times a day; the page then loads the recording straight
from the CDN, so a visitor waits for nothing and the Semantle API hears from
this project a handful of times a day rather than once per visitor.

A run that never reaches 100% still gets published: its best guess, marked
unconfirmed, so the board always shows today's attempt instead of a stale
answer from days ago. Before doing any work, this asks the game a single
question — is the recorded answer still good — so a run that is still
current costs one request and nothing is rewritten. For an unconfirmed
guess "still good" means the game still scores it the same as last time:
the search is deterministic, so an unchanged score means the puzzle word
has not changed either, and solving again would just repeat the same
failed search.

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
SOLVED_SIMILARITY = 100.0


def read_recording(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def is_current(recording: dict | None, client) -> bool:
    """True if there is no point solving again right now."""
    answer = (recording or {}).get("answer")
    if not answer:
        return False
    result = client.get_similarity(answer)
    if result is None:
        return False
    if recording.get("confirmed", True):
        return result.similarity >= SOLVED_SIMILARITY
    return result.similarity == recording.get("best_similarity")


def build_recording(vocabulary: Vocabulary, projection: BoardProjection, client) -> dict | None:
    """None means the game was unreachable for the whole run — not even one
    word got a score. Anything else is worth publishing: a confirmed answer
    when the search reached 100%, otherwise its best guess, marked
    unconfirmed.
    """
    events = [
        serialize(event, projection)
        for event in SemantleEngine(vocabulary, client).run()
    ]

    solved = next((e for e in events if e["type"] == "solved"), None)
    if solved is not None:
        return _stamped({"answer": solved["word"], "confirmed": True, "events": events})

    failed = next((e for e in events if e["type"] == "failed"), None)
    best_word = failed["best_word"] if failed else None
    if best_word is None:
        return None
    return _stamped(
        {
            "answer": best_word,
            "confirmed": False,
            "best_similarity": failed["best_similarity"],
            "events": events,
        }
    )


def _stamped(recording: dict) -> dict:
    return {**recording, "recorded_at": datetime.now(timezone.utc).isoformat()}


def main() -> None:
    client = SemantleClient()
    existing = read_recording(OUTPUT_PATH)
    if is_current(existing, client):
        print(f"'{existing['answer']}' is still today's best answer; nothing to publish")
        return

    print("The word has changed. Solving...")
    vocabulary = load_vocabulary()
    projection = BoardProjection(vocabulary, config.VOCAB_DIR / BASIS_FILENAME)
    recording = build_recording(vocabulary, projection, client)
    if recording is None:
        print("The game was unreachable all run; the previous recording is left in place.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(recording, ensure_ascii=False), encoding="utf-8")

    guesses = sum(1 for event in recording["events"] if event["type"] == "guess")
    label = "Solved" if recording["confirmed"] else "Best guess"
    print(f"{label} '{recording['answer']}' in {guesses} guesses, published to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
