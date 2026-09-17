"""Terminal presentation: consume engine events and print them."""

from __future__ import annotations

from cli.plotting import plot_history
from semantle.client import SemantleClient
from solver import events
from solver.engine import SemantleEngine
from solver.vocabulary import load_vocabulary


def format_event(event: events.Event) -> str | None:
    """Render one event as a line of terminal output, or None to stay silent."""
    if isinstance(event, events.RunStarted):
        return f"[INFO] Loaded {event.vocabulary_size} words. Solving..."
    if isinstance(event, events.Guess):
        marker = " [NEW BEST]" if event.is_best_so_far else ""
        rank = f" rank={event.rank}" if event.rank is not None else ""
        return (
            f"{event.guess_number:02d} | {event.word:<12} | "
            f"{event.similarity:6.2f}{rank}{marker}"
        )
    if isinstance(event, events.Solved):
        return (
            f"\n[SOLVED] The word is '{event.word}' "
            f"({event.total_guesses} guesses, {event.elapsed_seconds:.1f}s)"
        )
    if isinstance(event, events.Failed):
        return f"\n[STOPPED] {event.reason}"
    return None


def main() -> None:
    vocabulary = load_vocabulary()
    engine = SemantleEngine(vocabulary, SemantleClient())

    history: list[dict] = []
    for event in engine.run():
        line = format_event(event)
        if line is not None:
            print(line)
        if isinstance(event, events.Guess):
            history.append({
                "guess_number": event.guess_number,
                "similarity": event.similarity,
                "best_similarity": event.best_similarity,
                "is_best_so_far": event.is_best_so_far,
            })

    plot_history(history)
