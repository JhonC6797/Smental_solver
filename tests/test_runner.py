from datetime import datetime, timezone

from cli.runner import format_event
from solver import events


def test_formats_a_guess_with_its_score():
    line = format_event(events.Guess("כלב", 42.7, None, 5, False, "חתול", 60.0))
    assert "כלב" in line
    assert "42.7" in line


def test_marks_a_new_best():
    line = format_event(events.Guess("כלב", 61.0, None, 5, True, "כלב", 61.0))
    assert "NEW BEST" in line


def test_shows_the_rank_when_the_api_supplies_one():
    line = format_event(events.Guess("כלב", 61.0, 847, 5, True, "כלב", 61.0))
    assert "847" in line


def test_announces_the_answer():
    line = format_event(events.Solved("עץ", 42, 31.5))
    assert "עץ" in line


def test_diagnostics_produce_no_output():
    assert format_event(events.Diagnostics(guess_number=1)) is None


def test_run_started_is_reported():
    line = format_event(events.RunStarted(22000, datetime.now(timezone.utc)))
    assert "22000" in line
