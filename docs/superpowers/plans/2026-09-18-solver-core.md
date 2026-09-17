# Solver Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Semantle solver into a tested Python package whose search engine emits events instead of printing, fix the six confirmed bugs, and settle the 3D projection method by measurement.

**Architecture:** The flat root modules become four packages: `solver/` (pure search logic, no network printing, no display), `semantle/` (the game API client), `scripts/` (one-off manual tools), `cli/` (terminal presentation). The engine becomes a generator yielding typed events, so the same engine drives both the CLI and — in the follow-up web plan — the WebSocket server. `server/projection.py` is built here because it is pure deterministic math that the measurement decides.

**Tech Stack:** Python 3.13, numpy 2.3.5, pytest 8.4.2, requests.

**Spec:** [docs/superpowers/specs/2026-09-18-semantle-live-board-design.md](../specs/2026-09-18-semantle-live-board-design.md)

## Global Constraints

- `solver/` MUST NOT import from `server/`, `cli/`, or `scripts/`, and MUST NOT call `print`.
- `server/` MUST NOT reference algorithm-internal names; it only forwards events and adds position.
- Suspect constants are extracted to `solver/config.py` with their current values and NOT retuned in this plan: `BAD_WORD_THRESHOLD = 45.0`, `TEMPERATURE_FOCUSED = 4.0`, `TEMPERATURE_BROAD = 8.0`, `FOCUS_THRESHOLD = 65.0`, `HIGH_SCORE_THRESHOLD = 50.0`.
- `is_too_similar_fast` keeps its 3-letter-prefix rule and `is_clean_hebrew` keeps its `startswith` rule unchanged — both are in the spec's "measure first" bucket.
- Model vocabulary: `data/wiki.he.vec`, header `488936 300`. Built artifact goes in `data/vocab/`. Neither is committed.
- All new directories get an `__init__.py` so imports resolve from the repo root.

---

## File Structure

| File | Responsibility |
|---|---|
| `solver/config.py` | Every tunable constant and the anchor list, named |
| `solver/morphology.py` | Hebrew word filtering, stemming, duplicate detection |
| `solver/vocabulary.py` | `Vocabulary` value object + loading the built artifact |
| `solver/events.py` | The event types the engine emits |
| `solver/engine.py` | The search algorithm, as a generator |
| `semantle/client.py` | HTTP client for the game API, incl. the `distance` field |
| `scripts/build_vocab.py` | Converts `wiki.he.vec` into the compact artifact |
| `scripts/measure_projection.py` | Measures projection fidelity, prints a comparison |
| `server/projection.py` | 300-d vector → radius + unit direction |
| `cli/plotting.py` | The matplotlib summary chart (terminal only) |
| `cli/runner.py` | Consumes engine events and prints them |
| `run_cli.py` | Thin entry point |
| `tests/` | One test module per unit above |

Deleted at the end of Task 7: `config.py`, `utils.py`, `model_loader.py`, `api_client.py`, `solver.py`, `main.py`.

---

### Task 1: Configuration module

**Files:**
- Create: `solver/__init__.py`, `solver/config.py`
- Test: none (constants only; covered by consumers)

**Interfaces:**
- Consumes: nothing
- Produces: the constants listed below, imported by Tasks 2, 3, 5, 6, 8

- [ ] **Step 1: Create the package directory and config**

```python
# solver/config.py
"""Every tunable value in the solver, in one place.

Constants marked SUSPECT are known to be poorly calibrated (see section 7
of the design spec). They keep their original values here on purpose: they
are changed only once the live board can measure their effect.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_MODEL_PATH = PROJECT_ROOT / "data" / "wiki.he.vec"
VOCAB_DIR = PROJECT_ROOT / "data" / "vocab"
VECTORS_FILENAME = "vectors.npy"
WORDS_FILENAME = "words.json"

API_URL = "https://semantle.ishefi.com/api/distance"
REQUEST_TIMEOUT_SECONDS = 5
DELAY_BETWEEN_REQUESTS_SECONDS = 0.5
RATE_LIMIT_BACKOFF_SECONDS = 4
MAX_RATE_LIMIT_RETRIES = 3

VOCAB_LIMIT = 22000
EMBEDDING_DIMENSIONS = 300

MAX_ATTEMPTS = 60
MAX_CONSECUTIVE_FAILURES = 5
TOP_CANDIDATES_REPORTED = 30

FREQUENCY_BIAS_SPAN = -0.05
REPULSION_BASE = 0.4
REPULSION_STEP = 0.1
REPULSION_FLOOR = 0.3

# SUSPECT — unrelated words score 24-32, so 45 marks good hits as "bad".
BAD_WORD_THRESHOLD = 45.0
# SUSPECT — scores are 0-100, so exp(score/4) saturates to one-hot.
TEMPERATURE_FOCUSED = 4.0
TEMPERATURE_BROAD = 8.0
# SUSPECT — by the time this triggers the weighting is already one-hot.
FOCUS_THRESHOLD = 65.0
HIGH_SCORE_THRESHOLD = 50.0

INITIAL_ANCHORS = [
    "בית", "מלחמה", "ספר", "אוכל", "אדם",
    "מחשב", "מדינה", "ארץ", "שמיים", "אש",
    "ים", "שיר", "חוק", "נסיעה", "רופא",
]
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "from solver import config; print(config.VOCAB_LIMIT, len(config.INITIAL_ANCHORS))"`
Expected: `22000 15`

- [ ] **Step 3: Commit**

```bash
git add solver/__init__.py solver/config.py
git commit -m "refactor: extract solver constants into solver/config.py"
```

---

### Task 2: Morphology module and the three filter bugs

**Files:**
- Create: `solver/morphology.py`, `tests/__init__.py`, `tests/test_morphology.py`
- Test: `tests/test_morphology.py`

**Interfaces:**
- Consumes: nothing
- Produces: `is_clean_hebrew(word: str) -> bool`, `get_stem(word: str) -> str`, `is_too_similar_fast(candidate: str, tested_words: set[str]) -> bool`

Three confirmed bugs are fixed here. Bug 1: the length regex `{3,8}` rejects two-letter words, dropping the anchors `אש` and `ים` (both verified as valid guesses by the live API) and making answers like `יד` unreachable. Bug 2: the suffix blacklist rejects the real words `מזון`, `חזון`, `איזון`, `סוכר`, `מוכר` — its intent was filtering transliterated foreign names, so only the unambiguous multi-letter foreign markers survive. Bug 3: `get_stem` strips `המבכלו` from the front, but those are ordinary Hebrew root letters, so `ממלכה`, `מלה`, `בהמה`, `בובה` all collapse to the empty string and are treated as the same word.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_morphology.py
"""Regression tests for the word filter. Every word named here was verified
to be mishandled by the original implementation."""

import pytest

from solver.morphology import get_stem, is_clean_hebrew, is_too_similar_fast


@pytest.mark.parametrize("word", ["אש", "ים", "יד", "דם"])
def test_two_letter_words_are_accepted(word):
    """The original regex required 3-8 letters, silently dropping two of the
    15 configured anchors. The live API accepts 'אש' and scores it 31.92."""
    assert is_clean_hebrew(word) is True


@pytest.mark.parametrize("word", ["מזון", "חזון", "איזון", "סוכר", "מוכר"])
def test_real_words_are_not_rejected_by_the_suffix_blacklist(word):
    """If the daily answer is 'סוכר', the original solver could never win."""
    assert is_clean_hebrew(word) is True


@pytest.mark.parametrize("word", ["שוחמכר", "פערלאג", "רובינשטיין"])
def test_transliterated_foreign_names_are_still_rejected(word):
    assert is_clean_hebrew(word) is False


@pytest.mark.parametrize("word", ["a", "א", "אבגדהוזחט", "שלום!", "test"])
def test_non_words_are_rejected(word):
    assert is_clean_hebrew(word) is False


@pytest.mark.parametrize("word", ["ממלכה", "מלה", "בהמה", "בובה", "מלחמה"])
def test_stem_never_collapses_below_three_characters(word):
    """These all reduced to '' or a 2-char stem, so the duplicate filter
    treated them as the same word."""
    assert len(get_stem(word)) >= 3


def test_distinct_words_get_distinct_stems():
    assert get_stem("ממלכה") != get_stem("בובה")
    assert get_stem("מלה") != get_stem("בהמה")


def test_stem_still_strips_genuine_inflection():
    assert get_stem("ספרים") == get_stem("ספר")


def test_duplicate_detection_catches_inflections():
    assert is_too_similar_fast("ספרים", {"ספר"}) is True


def test_duplicate_detection_allows_unrelated_words():
    assert is_too_similar_fast("מחשב", {"ספר"}) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_morphology.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solver.morphology'`

- [ ] **Step 3: Write the implementation**

```python
# solver/morphology.py
"""Hebrew word filtering, stemming and duplicate detection.

The vocabulary comes from Wikipedia, so it is full of transliterated foreign
names and inflected forms that waste API calls. These helpers keep the
vocabulary to words a Semantle answer could plausibly be.
"""

import re

MIN_WORD_LENGTH = 2
MAX_WORD_LENGTH = 8
MIN_STEM_LENGTH = 3

_HEBREW_WORD = re.compile(rf"[א-ת]{{{MIN_WORD_LENGTH},{MAX_WORD_LENGTH}}}")
_PREFIX_LETTERS = re.compile(r"^[המבכלו]+")
_SUFFIX_FORMS = re.compile(r"(ים|ות|י|ה|נו)$")

# Endings that mark transliterated foreign names in Hebrew Wikipedia. Kept
# deliberately short: the original list also held 'זון', 'כר', 'ברג' and
# 'רגי', which reject the ordinary Hebrew words מזון, סוכר, זכר, שכר and ברג.
_FOREIGN_NAME_ENDINGS = ("שטיין", "לאג")

# Prefixes that, on a long word, usually signal a grammatical form rather
# than a dictionary entry. Left unchanged pending measurement (spec §7).
_GRAMMATICAL_PREFIXES = ("ו", "ב", "כ", "ל", "ד")
_GRAMMATICAL_PREFIX_MIN_LENGTH = 6


def is_clean_hebrew(word: str) -> bool:
    """True if the word is plausible as a Semantle answer."""
    if not _HEBREW_WORD.fullmatch(word):
        return False
    if (
        word.startswith(_GRAMMATICAL_PREFIXES)
        and len(word) >= _GRAMMATICAL_PREFIX_MIN_LENGTH
    ):
        return False
    return not word.endswith(_FOREIGN_NAME_ENDINGS)


def get_stem(word: str) -> str:
    """Strip prefix letters and inflection suffixes.

    A strip is applied only when at least MIN_STEM_LENGTH characters survive.
    The letters המבכלו are prefixes in some words and root letters in others,
    so stripping unconditionally turns ממלכה, מלה and בובה into the empty
    string and makes the duplicate filter treat them as one word.
    """
    for pattern in (_PREFIX_LETTERS, _SUFFIX_FORMS):
        stripped = pattern.sub("", word, count=1)
        if len(stripped) >= MIN_STEM_LENGTH:
            word = stripped
    return word


def is_too_similar_fast(candidate: str, tested_words: set[str]) -> bool:
    """True if the candidate is a near-duplicate of something already tried.

    The 3-character prefix rule below is aggressive and is a known suspect,
    but it is left unchanged until the board can measure how much of the
    vocabulary it burns (spec §7).
    """
    candidate_stem = get_stem(candidate)
    for tested in tested_words:
        tested_stem = get_stem(tested)
        if candidate_stem == tested_stem:
            return True
        if len(candidate_stem) >= 3 and len(tested_stem) >= 3:
            if candidate_stem[:3] == tested_stem[:3]:
                return True
        if candidate in tested or tested in candidate:
            return True
    return False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_morphology.py -v`
Expected: all PASS

- [ ] **Step 5: Verify the anchors are now all usable**

Run: `python -c "from solver.config import INITIAL_ANCHORS; from solver.morphology import is_clean_hebrew; print(sum(map(is_clean_hebrew, INITIAL_ANCHORS)), 'of', len(INITIAL_ANCHORS))"`
Expected: `15 of 15`

- [ ] **Step 6: Commit**

```bash
git add solver/morphology.py tests/__init__.py tests/test_morphology.py
git commit -m "fix: accept 2-letter words, stop rejecting real words, keep stems >= 3 chars"
```

---

### Task 3: Vocabulary artifact builder and loader

**Files:**
- Create: `solver/vocabulary.py`, `scripts/__init__.py`, `scripts/build_vocab.py`, `tests/test_vocabulary.py`
- Test: `tests/test_vocabulary.py`

**Interfaces:**
- Consumes: `solver.config`, `solver.morphology.is_clean_hebrew`
- Produces: `Vocabulary` (frozen dataclass with `words: list[str]`, `vectors: np.ndarray`, `word_to_index: dict[str, int]`), `load_vocabulary(directory: Path | None = None) -> Vocabulary`, `build_vocabulary(vec_path: Path, out_dir: Path, limit: int) -> Vocabulary`

`data/wiki.he.vec` is 1.23GB of text that the original code re-parsed on every start. It is converted once into `vectors.npy` plus `words.json` (~26MB) that load instantly. Words in the source file are ordered by descending frequency, which the engine's frequency bias relies on, so that order is preserved.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_vocabulary.py
import json

import numpy as np
import pytest

from solver.vocabulary import Vocabulary, build_vocabulary, load_vocabulary


@pytest.fixture
def fake_vec_file(tmp_path):
    """A miniature .vec file in the real format: a header line of
    '<word count> <dimensions>', then one line per word."""
    path = tmp_path / "fake.vec"
    rows = [
        ("שלום", [3.0, 4.0, 0.0]),   # norm 5, kept
        (",", [1.0, 0.0, 0.0]),       # punctuation, dropped
        ("אש", [0.0, 2.0, 0.0]),      # two letters, kept
        ("rubbish", [1.0, 1.0, 1.0]), # latin, dropped
        ("סוכר", [0.0, 0.0, 7.0]),    # kept
    ]
    lines = [f"{len(rows)} 3"]
    lines += [word + " " + " ".join(str(v) for v in vec) for word, vec in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_build_keeps_only_clean_hebrew_words(fake_vec_file, tmp_path):
    vocabulary = build_vocabulary(fake_vec_file, tmp_path / "out", limit=100)
    assert vocabulary.words == ["שלום", "אש", "סוכר"]


def test_build_normalises_vectors_to_unit_length(fake_vec_file, tmp_path):
    vocabulary = build_vocabulary(fake_vec_file, tmp_path / "out", limit=100)
    norms = np.linalg.norm(vocabulary.vectors, axis=1)
    assert np.allclose(norms, 1.0)


def test_build_preserves_source_frequency_order(fake_vec_file, tmp_path):
    """The engine's frequency bias assumes index 0 is the most common word."""
    vocabulary = build_vocabulary(fake_vec_file, tmp_path / "out", limit=100)
    assert vocabulary.words[0] == "שלום"


def test_build_respects_the_limit(fake_vec_file, tmp_path):
    vocabulary = build_vocabulary(fake_vec_file, tmp_path / "out", limit=2)
    assert len(vocabulary.words) == 2


def test_build_writes_files_that_load_back_identically(fake_vec_file, tmp_path):
    out_dir = tmp_path / "out"
    built = build_vocabulary(fake_vec_file, out_dir, limit=100)
    loaded = load_vocabulary(out_dir)
    assert loaded.words == built.words
    assert np.array_equal(loaded.vectors, built.vectors)


def test_word_to_index_maps_back_to_the_right_row(fake_vec_file, tmp_path):
    vocabulary = build_vocabulary(fake_vec_file, tmp_path / "out", limit=100)
    index = vocabulary.word_to_index["סוכר"]
    assert vocabulary.words[index] == "סוכר"


def test_loading_a_missing_artifact_explains_how_to_build_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_vocab"):
        load_vocabulary(tmp_path / "does-not-exist")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_vocabulary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solver.vocabulary'`

- [ ] **Step 3: Write the vocabulary module**

```python
# solver/vocabulary.py
"""The word list and its embedding matrix.

The raw FastText file is a multi-gigabyte text file. It is converted once
by scripts/build_vocab.py into a compact pair of files that load instantly;
nothing at runtime ever parses the .vec file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from solver import config
from solver.morphology import is_clean_hebrew


@dataclass(frozen=True)
class Vocabulary:
    """Words and their L2-normalised vectors, ordered by descending frequency."""

    words: list[str]
    vectors: np.ndarray
    word_to_index: dict[str, int] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "word_to_index", {word: i for i, word in enumerate(self.words)}
        )

    def __len__(self) -> int:
        return len(self.words)


def _normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


def build_vocabulary(vec_path: Path, out_dir: Path, limit: int) -> Vocabulary:
    """Parse a FastText .vec file and write the compact artifact."""
    words: list[str] = []
    rows: list[np.ndarray] = []

    with open(vec_path, encoding="utf-8") as handle:
        handle.readline()  # header: "<word count> <dimensions>"
        for line in handle:
            if len(words) >= limit:
                break
            parts = line.rstrip().split(" ")
            word = parts[0]
            if not is_clean_hebrew(word):
                continue
            try:
                rows.append(np.array(parts[1:], dtype=np.float32))
            except ValueError:
                continue
            words.append(word)

    vectors = _normalise(np.vstack(rows))
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / config.VECTORS_FILENAME, vectors)
    (out_dir / config.WORDS_FILENAME).write_text(
        json.dumps(words, ensure_ascii=False), encoding="utf-8"
    )
    return Vocabulary(words=words, vectors=vectors)


def load_vocabulary(directory: Path | None = None) -> Vocabulary:
    """Load the artifact built by scripts/build_vocab.py."""
    directory = directory or config.VOCAB_DIR
    vectors_path = directory / config.VECTORS_FILENAME
    words_path = directory / config.WORDS_FILENAME
    if not vectors_path.exists() or not words_path.exists():
        raise FileNotFoundError(
            f"No vocabulary artifact in {directory}. "
            "Build it with: python -m scripts.build_vocab"
        )
    words = json.loads(words_path.read_text(encoding="utf-8"))
    return Vocabulary(words=words, vectors=np.load(vectors_path))
```

- [ ] **Step 4: Write the build script**

```python
# scripts/build_vocab.py
"""Convert data/wiki.he.vec into the compact vocabulary artifact.

Run once after downloading the model:
    python -m scripts.build_vocab
"""

from solver import config
from solver.vocabulary import build_vocabulary


def main() -> None:
    if not config.RAW_MODEL_PATH.exists():
        raise SystemExit(
            f"Model not found at {config.RAW_MODEL_PATH}.\n"
            "Download it from "
            "https://dl.fbaipublicfiles.com/fasttext/vectors-wiki/wiki.he.vec"
        )
    print(f"Reading {config.RAW_MODEL_PATH} (this takes a minute)...")
    vocabulary = build_vocabulary(
        config.RAW_MODEL_PATH, config.VOCAB_DIR, config.VOCAB_LIMIT
    )
    print(f"Wrote {len(vocabulary)} words to {config.VOCAB_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_vocabulary.py -v`
Expected: all PASS

- [ ] **Step 6: Build the real artifact**

Run: `python -m scripts.build_vocab`
Expected: prints `Wrote 22000 words to ...data/vocab`. If fewer than 22000, the filter is stricter than intended — report the count rather than adjusting the filter.

- [ ] **Step 7: Commit**

```bash
git add solver/vocabulary.py scripts/__init__.py scripts/build_vocab.py tests/test_vocabulary.py
git commit -m "feat: build and load a compact vocabulary artifact"
```

---

### Task 4: Semantle API client

**Files:**
- Create: `semantle/__init__.py`, `semantle/client.py`, `tests/test_client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: `solver.config`
- Produces: `GuessResult` (frozen dataclass: `word: str`, `similarity: float`, `rank: int | None`), `SemantleClient.get_similarity(word: str) -> GuessResult | None`

Two changes. The `distance` field is now captured: the live API returns it as the guess's rank within the answer's nearest 1000 words, or `-1` when outside them, which is an exact closeness signal from the game's own model. It is recorded and displayed but **not** fed to the algorithm. Separately, the original retried HTTP 429 by calling itself recursively with no bound, so a sustained rate limit recursed forever; retries are now capped.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_client.py
import pytest

from semantle.client import GuessResult, SemantleClient


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """Stands in for requests.Session, returning queued responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.headers = {}
        self.call_count = 0

    def get(self, url, params=None, timeout=None):
        self.call_count += 1
        return self._responses.pop(0)


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr("semantle.client.time.sleep", lambda _seconds: None)


def _client(session):
    client = SemantleClient()
    client.session = session
    return client


def test_parses_similarity_and_rank(no_sleep):
    payload = [{"guess": "שלום", "similarity": 23.95, "distance": 847}]
    client = _client(FakeSession([FakeResponse(200, payload)]))
    assert client.get_similarity("שלום") == GuessResult("שלום", 23.95, 847)


def test_rank_is_none_when_outside_the_top_thousand(no_sleep):
    payload = [{"guess": "שלום", "similarity": 23.95, "distance": -1}]
    client = _client(FakeSession([FakeResponse(200, payload)]))
    assert client.get_similarity("שלום").rank is None


def test_retries_once_after_a_rate_limit(no_sleep):
    payload = [{"guess": "אש", "similarity": 31.92, "distance": -1}]
    session = FakeSession([FakeResponse(429), FakeResponse(200, payload)])
    assert _client(session).get_similarity("אש").similarity == 31.92
    assert session.call_count == 2


def test_gives_up_after_the_retry_limit(no_sleep):
    """The original recursed without a bound and never returned."""
    session = FakeSession([FakeResponse(429)] * 10)
    assert _client(session).get_similarity("אש") is None
    assert session.call_count <= 4


def test_returns_none_on_an_empty_payload(no_sleep):
    client = _client(FakeSession([FakeResponse(200, [])]))
    assert client.get_similarity("אש") is None


def test_returns_none_when_the_request_raises(no_sleep):
    class ExplodingSession(FakeSession):
        def get(self, url, params=None, timeout=None):
            raise OSError("network down")

    assert _client(ExplodingSession([])).get_similarity("אש") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'semantle'`

- [ ] **Step 3: Write the implementation**

```python
# semantle/client.py
"""HTTP client for the Semantle game API.

A successful response looks like:
    [{"guess": "שלום", "similarity": 23.95, "distance": -1,
      "egg": null, "solver_count": null, "guess_number": 0}]

`similarity` is a percentage on a 0-100 scale; unrelated words score 24-32.
`distance` is the guess's rank within the answer's nearest 1000 words in the
game's own model, or -1 when it is outside them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from solver import config

_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
)


@dataclass(frozen=True)
class GuessResult:
    word: str
    similarity: float
    rank: int | None


class SemantleClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _BROWSER_USER_AGENT})

    def get_similarity(self, word: str) -> GuessResult | None:
        """Score one word, or return None if the game could not be reached."""
        for _attempt in range(config.MAX_RATE_LIMIT_RETRIES + 1):
            time.sleep(config.DELAY_BETWEEN_REQUESTS_SECONDS)
            try:
                response = self.session.get(
                    config.API_URL,
                    params={"word": word},
                    timeout=config.REQUEST_TIMEOUT_SECONDS,
                )
            except Exception:
                return None

            if response.status_code == 429:
                time.sleep(config.RATE_LIMIT_BACKOFF_SECONDS)
                continue
            if response.status_code != 200:
                return None
            return self._parse(word, response)
        return None

    @staticmethod
    def _parse(word: str, response) -> GuessResult | None:
        try:
            payload = response.json()
        except Exception:
            return None
        if not isinstance(payload, list) or not payload:
            return None
        similarity = payload[0].get("similarity")
        if similarity is None:
            return None
        distance = payload[0].get("distance", -1)
        return GuessResult(
            word=word,
            similarity=float(similarity),
            rank=None if distance is None or distance < 0 else int(distance),
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_client.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add semantle/__init__.py semantle/client.py tests/test_client.py
git commit -m "feat: capture the API rank field and bound rate-limit retries"
```

---

### Task 5: Event types

**Files:**
- Create: `solver/events.py`
- Test: none (plain data; exercised by Task 6)

**Interfaces:**
- Consumes: nothing
- Produces: `RunStarted`, `Guess`, `Solved`, `Failed`, `Diagnostics`, and the union alias `Event`

The split matters: the first four are true of any search algorithm and form the stable contract. `Diagnostics` carries whatever the current algorithm happens to compute, in three open dictionaries, so a future algorithm can report different internals without changing the protocol or the frontend.

- [ ] **Step 1: Write the module**

```python
# solver/events.py
"""What the engine emits.

Core events (RunStarted, Guess, Solved, Failed) are true of ANY search
algorithm; consumers may rely on them. Diagnostics is deliberately generic:
its three dictionaries hold whatever the current algorithm computes, keyed
by name, so replacing the algorithm changes the contents and never the
contract. Consumers render Diagnostics by VALUE TYPE, never by key name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class RunStarted:
    vocabulary_size: int
    started_at: datetime


@dataclass(frozen=True)
class Guess:
    word: str
    similarity: float
    rank: int | None
    guess_number: int
    is_best_so_far: bool
    best_word: str
    best_similarity: float


@dataclass(frozen=True)
class Solved:
    word: str
    total_guesses: int
    elapsed_seconds: float


@dataclass(frozen=True)
class Failed:
    reason: str


@dataclass(frozen=True)
class Diagnostics:
    """Algorithm internals for the guess that is about to be made."""

    guess_number: int
    scalars: dict[str, float] = field(default_factory=dict)
    directions: dict[str, np.ndarray] = field(default_factory=dict)
    word_scores: dict[str, list[tuple[str, float]]] = field(default_factory=dict)


Event = RunStarted | Guess | Solved | Failed | Diagnostics
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "from solver.events import Guess; print(Guess('אש', 31.9, None, 1, True, 'אש', 31.9))"`
Expected: a `Guess(...)` repr

- [ ] **Step 3: Commit**

```bash
git add solver/events.py
git commit -m "feat: add the engine event contract"
```

---

### Task 6: The engine as an event generator

**Files:**
- Create: `solver/engine.py`, `tests/test_engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Vocabulary`, `SemantleClient` (anything with `get_similarity(word) -> GuessResult | None`), `solver.events`, `solver.morphology.is_too_similar_fast`, `solver.config`
- Produces: `SemantleEngine(vocabulary, client, max_attempts=config.MAX_ATTEMPTS)` with `run() -> Iterator[Event]`

The algorithm is ported unchanged apart from one confirmed bug: the original did `continue` on a failed API call *before* incrementing the attempt counter, while having already added the word to the tested set. A single transient network error therefore removed the 60-attempt ceiling and permanently poisoned the duplicate filter with a word that was never scored. Here the attempt counter always advances, a word joins the tested set only once it has a real score, and a run of consecutive failures aborts.

The anchor probes now count as guesses and are emitted as `Guess` events, because they are real API calls that must appear on the board.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_engine.py
import numpy as np
import pytest

from semantle.client import GuessResult
from solver import events
from solver.engine import SemantleEngine
from solver.vocabulary import Vocabulary


@pytest.fixture
def vocabulary():
    words = ["בית", "אוכל", "אדם", "מחשב", "כלב", "חתול", "שולחן", "מכונית"]
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return Vocabulary(words=words, vectors=vectors)


class ScriptedClient:
    """Returns a fixed score per word; unlisted words get `default`."""

    def __init__(self, scores, default=20.0):
        self.scores = scores
        self.default = default
        self.asked = []

    def get_similarity(self, word):
        self.asked.append(word)
        return GuessResult(word, self.scores.get(word, self.default), None)


class FailingClient:
    def __init__(self):
        self.asked = []

    def get_similarity(self, word):
        self.asked.append(word)
        return None


def run(engine):
    return list(engine.run())


def test_first_event_is_run_started(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({})))
    assert isinstance(stream[0], events.RunStarted)
    assert stream[0].vocabulary_size == len(vocabulary)


def test_anchor_probes_are_emitted_as_guesses(vocabulary):
    """Anchors are real API calls and must appear on the board."""
    stream = run(SemantleEngine(vocabulary, ScriptedClient({})))
    guessed = [e.word for e in stream if isinstance(e, events.Guess)]
    assert "בית" in guessed


def test_guess_numbers_increase_by_one(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=3))
    numbers = [e.guess_number for e in stream if isinstance(e, events.Guess)]
    assert numbers == list(range(1, len(numbers) + 1))


def test_reaching_one_hundred_emits_solved(vocabulary):
    client = ScriptedClient({"חתול": 100.0}, default=10.0)
    stream = run(SemantleEngine(vocabulary, client))
    solved = [e for e in stream if isinstance(e, events.Solved)]
    assert len(solved) == 1
    assert solved[0].word == "חתול"


def test_no_guesses_are_made_after_solving(vocabulary):
    client = ScriptedClient({"בית": 100.0})
    stream = run(SemantleEngine(vocabulary, client))
    assert isinstance(stream[-1], events.Solved)
    assert len(client.asked) == 1


def test_words_are_never_guessed_twice(vocabulary):
    client = ScriptedClient({})
    run(SemantleEngine(vocabulary, client, max_attempts=6))
    assert len(client.asked) == len(set(client.asked))


def test_a_persistently_failing_api_stops_the_run(vocabulary):
    """The original looped over the whole vocabulary without advancing."""
    client = FailingClient()
    stream = run(SemantleEngine(vocabulary, client, max_attempts=60))
    assert isinstance(stream[-1], events.Failed)
    assert len(client.asked) < 20


def test_an_unscored_word_does_not_poison_the_duplicate_filter(vocabulary):
    engine = SemantleEngine(vocabulary, FailingClient())
    run(engine)
    assert engine.tested_words == set()


def test_diagnostics_precede_the_guess_they_describe(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=2))
    diagnostics = [e for e in stream if isinstance(e, events.Diagnostics)]
    assert diagnostics
    for diagnostic in diagnostics:
        following = [
            e for e in stream[stream.index(diagnostic):]
            if isinstance(e, events.Guess)
        ]
        assert following[0].guess_number == diagnostic.guess_number


def test_diagnostics_carry_the_target_estimate_as_a_direction(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=2))
    diagnostic = next(e for e in stream if isinstance(e, events.Diagnostics))
    target = diagnostic.directions["target_estimate"]
    assert target.shape == (vocabulary.vectors.shape[1],)


def test_running_out_of_attempts_emits_failed(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=1))
    assert isinstance(stream[-1], events.Failed)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solver.engine'`

- [ ] **Step 3: Write the implementation**

```python
# solver/engine.py
"""The search algorithm.

Two phases. First it probes a fixed list of anchor words to find a region of
meaning that scores well. Then it repeatedly estimates where the answer is —
as a softmax-weighted blend of the anchors it has scored, pushed away from
regions that scored badly — and guesses the nearest unused word to that
estimate. Above FOCUS_THRESHOLD it switches to plain nearest-neighbour
search around the best word found so far.

The engine yields events and never prints. It knows nothing about the server
or the board.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime, timezone

import numpy as np

from solver import config, events
from solver.morphology import is_too_similar_fast
from solver.vocabulary import Vocabulary

_GRAVITY_MODE = 0.0
_NEAREST_NEIGHBOUR_MODE = 1.0
_SOLVED_SIMILARITY = 100.0


class SemantleEngine:
    def __init__(
        self,
        vocabulary: Vocabulary,
        client,
        max_attempts: int = config.MAX_ATTEMPTS,
    ) -> None:
        self.vocabulary = vocabulary
        self.client = client
        self.max_attempts = max_attempts

        self.checked_indices: set[int] = set()
        self.tested_words: set[str] = set()
        self.scored_indices: list[int] = []
        self.scored_similarities: list[float] = []
        self.bad_indices: list[int] = []

        self.best_word: str | None = None
        self.best_similarity = -1.0
        self.stagnant_count = 0
        self.guess_number = 0

        # Words arrive in descending frequency order, so a gentle linear
        # penalty nudges the search towards commoner words.
        self.frequency_bias = np.linspace(
            0.0, config.FREQUENCY_BIAS_SPAN, len(vocabulary), dtype=np.float32
        )

    def run(self) -> Iterator[events.Event]:
        started = time.monotonic()
        yield events.RunStarted(
            vocabulary_size=len(self.vocabulary),
            started_at=datetime.now(timezone.utc),
        )

        for event in self._probe_anchors():
            yield event
            if self._is_solved():
                yield self._solved(started)
                return

        if not self.scored_similarities:
            yield events.Failed(reason="no anchor word returned a usable score")
            return

        for event in self._search():
            yield event
            if isinstance(event, events.Failed):
                return
            if self._is_solved():
                yield self._solved(started)
                return

        yield events.Failed(reason="ran out of attempts before reaching 100%")

    def _is_solved(self) -> bool:
        return self.best_similarity >= _SOLVED_SIMILARITY

    def _solved(self, started: float) -> events.Solved:
        return events.Solved(
            word=self.best_word,
            total_guesses=self.guess_number,
            elapsed_seconds=time.monotonic() - started,
        )

    def _probe_anchors(self) -> Iterator[events.Event]:
        for anchor in config.INITIAL_ANCHORS:
            index = self.vocabulary.word_to_index.get(anchor)
            if index is None:
                continue
            guess = self._submit(index, mark_bad=False)
            if guess is not None:
                yield guess

    def _search(self) -> Iterator[events.Event]:
        attempt = 0
        consecutive_failures = 0

        while attempt < self.max_attempts:
            attempt += 1  # always advances, even when the API call fails
            scores, target, scalars = self._score_candidates()
            index = self._pick_candidate(scores)
            if index is None:
                yield events.Failed(reason="no unused candidate words remain")
                return

            yield self._diagnostics(scores, target, scalars)

            guess = self._submit(index, mark_bad=True)
            if guess is None:
                consecutive_failures += 1
                if consecutive_failures >= config.MAX_CONSECUTIVE_FAILURES:
                    yield events.Failed(reason="the Semantle API kept failing")
                    return
                continue

            consecutive_failures = 0
            yield guess

    def _score_candidates(self) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
        vectors = self.vocabulary.vectors
        scalars = {"stagnant_count": float(self.stagnant_count)}

        if self.best_similarity >= config.FOCUS_THRESHOLD:
            scalars["mode"] = _NEAREST_NEIGHBOUR_MODE
            best_index = self.scored_indices[int(np.argmax(self.scored_similarities))]
            target = vectors[best_index]
            scores = vectors @ target
        else:
            scalars["mode"] = _GRAVITY_MODE
            target, weights = self._estimate_target()
            scalars["temperature"] = self._temperature()
            scalars["effective_anchor_count"] = float(1.0 / np.sum(weights**2))
            scores = vectors @ target
            if self.bad_indices:
                repulsion = np.max(vectors @ vectors[self.bad_indices].T, axis=1)
                penalty = config.REPULSION_BASE + (
                    self.stagnant_count * config.REPULSION_STEP
                )
                scalars["penalty_weight"] = float(penalty)
                scores = scores - penalty * np.maximum(
                    0.0, repulsion - config.REPULSION_FLOOR
                )

        scores = scores + self.frequency_bias
        if self.checked_indices:
            scores[list(self.checked_indices)] = -np.inf
        return scores, target, scalars

    def _temperature(self) -> float:
        if self.best_similarity >= config.HIGH_SCORE_THRESHOLD:
            return config.TEMPERATURE_FOCUSED
        return config.TEMPERATURE_BROAD

    def _estimate_target(self) -> tuple[np.ndarray, np.ndarray]:
        observed = np.array(self.scored_similarities, dtype=np.float32)
        weights = np.exp(observed / self._temperature())
        weights = weights / np.sum(weights)
        target = weights @ self.vocabulary.vectors[self.scored_indices]
        norm = np.linalg.norm(target)
        if norm > 0:
            target = target / norm
        return target.astype(np.float32), weights

    def _pick_candidate(self, scores: np.ndarray) -> int | None:
        for index in np.argsort(scores)[::-1]:
            index = int(index)
            word = self.vocabulary.words[index]
            if word in self.tested_words:
                continue
            if is_too_similar_fast(word, self.tested_words):
                self.checked_indices.add(index)
                continue
            return index
        return None

    def _diagnostics(
        self, scores: np.ndarray, target: np.ndarray, scalars: dict[str, float]
    ) -> events.Diagnostics:
        finite = np.isfinite(scores)
        ranked = np.argsort(scores)[::-1][: config.TOP_CANDIDATES_REPORTED]
        top = [
            (self.vocabulary.words[int(i)], float(scores[int(i)]))
            for i in ranked
            if finite[int(i)]
        ]
        return events.Diagnostics(
            guess_number=self.guess_number + 1,
            scalars=scalars,
            directions={"target_estimate": np.asarray(target, dtype=np.float32)},
            word_scores={"top_candidates": top},
        )

    def _submit(self, index: int, mark_bad: bool) -> events.Guess | None:
        """Score one word and fold the result into the engine's state."""
        word = self.vocabulary.words[index]
        self.checked_indices.add(index)

        result = self.client.get_similarity(word)
        if result is None:
            # Deliberately NOT added to tested_words: a word that was never
            # scored must not block its whole family from being guessed.
            return None

        self.tested_words.add(word)
        self.guess_number += 1

        if result.similarity > 0:
            self.scored_indices.append(index)
            self.scored_similarities.append(result.similarity)

        is_best = result.similarity > self.best_similarity
        if is_best:
            self.best_word = word
            self.best_similarity = result.similarity
            self.stagnant_count = 0
        else:
            self.stagnant_count += 1
            if mark_bad and result.similarity < config.BAD_WORD_THRESHOLD:
                self.bad_indices.append(index)

        return events.Guess(
            word=word,
            similarity=result.similarity,
            rank=result.rank,
            guess_number=self.guess_number,
            is_best_so_far=is_best,
            best_word=self.best_word,
            best_similarity=self.best_similarity,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_engine.py -v`
Expected: all PASS

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add solver/engine.py tests/test_engine.py
git commit -m "feat: engine yields events; fix the loop that never advanced on API failure"
```

---

### Task 7: CLI entry point, and removing the old modules

**Files:**
- Create: `cli/__init__.py`, `cli/plotting.py`, `cli/runner.py`, `run_cli.py`
- Delete: `config.py`, `utils.py`, `model_loader.py`, `api_client.py`, `solver.py`, `main.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `solver.engine.SemantleEngine`, `solver.events`, `solver.vocabulary.load_vocabulary`, `semantle.client.SemantleClient`
- Produces: `format_event(event) -> str | None`, `plot_history(history) -> None`, `main() -> None`

This closes the last confirmed bug: matplotlib was imported at module level inside `utils.py` and called from the solver, which pulls a full graphics stack into any process that touches word filtering. It now lives in `cli/`, which is the only place that draws anything.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runner.py
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cli'`

- [ ] **Step 3: Write the plotting module**

```python
# cli/plotting.py
"""The end-of-run summary chart.

Lives here, not in the solver, so that importing the solver never drags in
a graphics stack. Only the terminal runner draws anything.
"""

from __future__ import annotations


def plot_history(history: list[dict]) -> None:
    """Draw score-per-attempt with the running best overlaid."""
    if not history:
        return

    import matplotlib.pyplot as plt  # imported lazily: it is slow to load

    attempts = [row["guess_number"] for row in history]
    similarities = [row["similarity"] for row in history]
    best = [row["best_similarity"] for row in history]

    plt.figure(figsize=(10, 5))
    plt.plot(attempts, similarities, marker="o", linestyle="-",
             color="#3498db", alpha=0.6, label="Guess score")
    plt.plot(attempts, best, linestyle="--", color="#e74c3c",
             linewidth=2, label="Best so far")
    for row in history:
        if row["is_best_so_far"]:
            plt.plot(row["guess_number"], row["similarity"], marker="*",
                     markersize=12, color="#f1c40f")

    plt.title("Semantle Solver Progress", fontsize=14, fontweight="bold")
    plt.xlabel("Guess #", fontsize=12)
    plt.ylabel("Similarity (%)", fontsize=12)
    plt.ylim(0, 105)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper left")
    plt.tight_layout()
    plt.show()
```

- [ ] **Step 4: Write the runner**

```python
# cli/runner.py
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
```

- [ ] **Step 5: Write the entry point**

```python
# run_cli.py
"""Run the solver in the terminal: python run_cli.py"""

from cli.runner import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_runner.py -v`
Expected: all PASS

- [ ] **Step 7: Delete the superseded root modules**

```bash
git rm config.py utils.py model_loader.py api_client.py solver.py main.py
```

- [ ] **Step 8: Verify nothing still imports them**

Run: `python -m pytest -v && python -c "import cli.runner, solver.engine, semantle.client"`
Expected: all tests PASS and the import succeeds with no error

- [ ] **Step 9: Run the solver for real**

Run: `python run_cli.py`
Expected: anchors are scored, guesses stream, and the run ends in `[SOLVED]` or `[STOPPED]`. Record the guess count — it is the baseline the fixes are measured against.

- [ ] **Step 10: Commit**

```bash
git add cli/ run_cli.py tests/test_runner.py
git commit -m "refactor: move terminal output and plotting into cli/, drop the old root modules"
```

---

### Task 8: Projection measurement

**Files:**
- Create: `scripts/measure_projection.py`
- Test: none (a measurement tool; its output is the deliverable)

**Interfaces:**
- Consumes: `solver.vocabulary.load_vocabulary`
- Produces: `fit_pca_basis(vectors, components=3) -> tuple[np.ndarray, np.ndarray]`, `fit_landmark_basis(vocabulary, landmark_words) -> LandmarkBasis`, and a printed comparison

Position on the board is radius (from the score, exact) plus direction (from meaning). Direction compresses 300 dimensions onto a sphere's two degrees of freedom, and the choice decides whether related words actually land near each other. This script settles it with numbers instead of taste.

Two static methods are compared. Local MDS from the spec is deliberately excluded here: it depends on the guess order of a live run, so it cannot be scored against a fixed vocabulary, and it is only worth building if neither static method is good enough.

Two metrics: rank correlation between 300-d cosine and 3-d angular similarity over random pairs, and neighbour recall — of each sample word's true 20 nearest neighbours, how many stay in its 3-d nearest 20.

- [ ] **Step 1: Write the script**

```python
# scripts/measure_projection.py
"""Compare candidate 3D projections and print the numbers.

Run: python -m scripts.measure_projection
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solver.vocabulary import Vocabulary, load_vocabulary

SAMPLE_PAIRS = 20000
SAMPLE_WORDS = 300
NEIGHBOURS = 20
RANDOM_SEED = 0

LANDMARK_WORDS = [
    "בית", "מלחמה", "ספר", "אוכל", "אדם", "מחשב", "מדינה", "ארץ",
    "שמיים", "אש", "ים", "שיר", "חוק", "נסיעה", "רופא", "כסף",
    "ילד", "מים", "זמן", "עבודה", "מוזיקה", "צבא", "בריאות", "אהבה",
    "מכונית", "עיר", "חיה", "צמח", "מזון", "לימוד",
]


@dataclass
class LandmarkBasis:
    indices: list[int]
    directions: np.ndarray  # (landmarks, 3), unit rows


def fit_pca_basis(vectors: np.ndarray, components: int = 3):
    """Return (mean, basis) where basis is (dimensions, components)."""
    mean = vectors.mean(axis=0)
    centred = vectors - mean
    _u, _s, vt = np.linalg.svd(centred, full_matrices=False)
    return mean, vt[:components].T


def _fibonacci_sphere(count: int) -> np.ndarray:
    """Evenly spread unit vectors, so landmarks do not clump."""
    indices = np.arange(count, dtype=np.float64) + 0.5
    phi = np.arccos(1 - 2 * indices / count)
    theta = np.pi * (1 + 5**0.5) * indices
    return np.stack(
        [np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)],
        axis=1,
    )


def fit_landmark_basis(vocabulary: Vocabulary, words: list[str]) -> LandmarkBasis:
    present = [w for w in words if w in vocabulary.word_to_index]
    missing = sorted(set(words) - set(present))
    if missing:
        print(f"  (landmarks absent from the vocabulary: {', '.join(missing)})")
    indices = [vocabulary.word_to_index[w] for w in present]
    return LandmarkBasis(indices=indices, directions=_fibonacci_sphere(len(indices)))


def _unit(rows: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return rows / norms


def project_pca(vectors: np.ndarray, mean, basis) -> np.ndarray:
    return _unit((vectors - mean) @ basis)


def project_landmarks(vectors: np.ndarray, vocabulary, basis: LandmarkBasis):
    affinity = vectors @ vocabulary.vectors[basis.indices].T
    weights = np.exp(affinity * 8.0)
    weights /= weights.sum(axis=1, keepdims=True)
    return _unit(weights @ basis.directions)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    rank_a = np.argsort(np.argsort(a)).astype(np.float64)
    rank_b = np.argsort(np.argsort(b)).astype(np.float64)
    rank_a -= rank_a.mean()
    rank_b -= rank_b.mean()
    return float(rank_a @ rank_b / (np.linalg.norm(rank_a) * np.linalg.norm(rank_b)))


def evaluate(name: str, vocabulary: Vocabulary, projected: np.ndarray) -> None:
    rng = np.random.default_rng(RANDOM_SEED)
    size = len(vocabulary)

    left = rng.integers(0, size, SAMPLE_PAIRS)
    right = rng.integers(0, size, SAMPLE_PAIRS)
    true_similarity = np.sum(vocabulary.vectors[left] * vocabulary.vectors[right], axis=1)
    board_similarity = np.sum(projected[left] * projected[right], axis=1)
    correlation = _spearman(true_similarity, board_similarity)

    sample = rng.choice(size, SAMPLE_WORDS, replace=False)
    kept = []
    for index in sample:
        true_top = np.argpartition(
            -(vocabulary.vectors @ vocabulary.vectors[index]), NEIGHBOURS + 1
        )[: NEIGHBOURS + 1]
        board_top = np.argpartition(
            -(projected @ projected[index]), NEIGHBOURS + 1
        )[: NEIGHBOURS + 1]
        kept.append(len(set(true_top) & set(board_top)) / NEIGHBOURS)
    recall = float(np.mean(kept))

    print(f"{name:<12} rank correlation {correlation:+.3f}   "
          f"neighbour recall@{NEIGHBOURS} {recall:.1%}")


def main() -> None:
    vocabulary = load_vocabulary()
    print(f"Vocabulary: {len(vocabulary)} words, "
          f"{vocabulary.vectors.shape[1]} dimensions\n")

    mean, basis = fit_pca_basis(vocabulary.vectors)
    evaluate("PCA", vocabulary, project_pca(vocabulary.vectors, mean, basis))

    landmarks = fit_landmark_basis(vocabulary, LANDMARK_WORDS)
    evaluate("Landmarks", vocabulary,
             project_landmarks(vocabulary.vectors, vocabulary, landmarks))

    print("\nHigher is better on both. Pick the winner for server/projection.py.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the measurement**

Run: `python -m scripts.measure_projection`
Expected: two lines of numbers. Record them — they are the evidence for Task 9.

- [ ] **Step 3: Commit**

```bash
git add scripts/measure_projection.py
git commit -m "feat: measure projection fidelity for PCA and landmark layouts"
```

---

### Task 9: The projection module

**Files:**
- Create: `server/__init__.py`, `server/projection.py`, `tests/test_projection.py`
- Test: `tests/test_projection.py`

**Interfaces:**
- Consumes: `solver.vocabulary.Vocabulary`, and the winning fit function from Task 8
- Produces: `BoardProjection(vocabulary)` with `place(word: str, similarity: float) -> Position`, `place_vector(vector: np.ndarray, similarity: float) -> Position`, and `Position` (frozen dataclass: `x, y, z, radius: float`)

Radius is linear in the score and carries no approximation: `radius = BOARD_RADIUS * (1 - similarity / 100)`, so 100% lands exactly at the centre. Direction comes from the method Task 8's numbers chose.

The determinism test is the important one. If a word's direction can change between runs, the board stops being a map, and the original spec's whole objection to recomputing the layout returns.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_projection.py
import numpy as np
import pytest

from server.projection import BOARD_RADIUS, BoardProjection, Position
from solver.vocabulary import Vocabulary


@pytest.fixture
def vocabulary():
    words = ["בית", "אוכל", "אדם", "מחשב", "כלב", "חתול"]
    rng = np.random.default_rng(1)
    vectors = rng.normal(size=(len(words), 16)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return Vocabulary(words=words, vectors=vectors)


def test_a_perfect_score_lands_on_the_centre(vocabulary):
    position = BoardProjection(vocabulary).place("כלב", 100.0)
    assert position.radius == pytest.approx(0.0)
    assert (position.x, position.y, position.z) == pytest.approx((0.0, 0.0, 0.0))


def test_a_zero_score_lands_on_the_outer_shell(vocabulary):
    assert BoardProjection(vocabulary).place("כלב", 0.0).radius == pytest.approx(
        BOARD_RADIUS
    )


def test_radius_is_linear_in_the_score(vocabulary):
    projection = BoardProjection(vocabulary)
    assert projection.place("כלב", 50.0).radius == pytest.approx(BOARD_RADIUS * 0.5)
    assert projection.place("כלב", 75.0).radius == pytest.approx(BOARD_RADIUS * 0.25)


def test_the_point_actually_sits_at_that_radius(vocabulary):
    position = BoardProjection(vocabulary).place("כלב", 40.0)
    length = np.linalg.norm([position.x, position.y, position.z])
    assert length == pytest.approx(position.radius, rel=1e-5)


def test_direction_is_independent_of_the_score(vocabulary):
    projection = BoardProjection(vocabulary)
    near = projection.place("כלב", 90.0)
    far = projection.place("כלב", 10.0)
    near_direction = np.array([near.x, near.y, near.z]) / near.radius
    far_direction = np.array([far.x, far.y, far.z]) / far.radius
    assert near_direction == pytest.approx(far_direction, abs=1e-5)


def test_the_same_word_always_lands_in_the_same_direction(vocabulary):
    """A fresh projection must reproduce the layout exactly, or the board
    stops being a map."""
    first = BoardProjection(vocabulary).place("חתול", 55.0)
    second = BoardProjection(vocabulary).place("חתול", 55.0)
    assert (first.x, first.y, first.z) == pytest.approx(
        (second.x, second.y, second.z)
    )


def test_a_degenerate_vector_still_yields_a_unit_direction(vocabulary):
    """A vector that projects to zero length has no direction mathematically;
    the fallback must be fixed, not random."""
    projection = BoardProjection(vocabulary)
    zero = np.zeros(vocabulary.vectors.shape[1], dtype=np.float32)
    first = projection.place_vector(zero, 50.0)
    second = projection.place_vector(zero, 50.0)
    length = np.linalg.norm([first.x, first.y, first.z])
    assert length == pytest.approx(first.radius, rel=1e-5)
    assert (first.x, first.y, first.z) == pytest.approx((second.x, second.y, second.z))


def test_an_unknown_word_is_rejected(vocabulary):
    with pytest.raises(KeyError):
        BoardProjection(vocabulary).place("מילה־שאיננה", 50.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_projection.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server.projection'`

- [ ] **Step 3: Write the implementation**

Use the method Task 8's numbers selected. The version below uses PCA; if the landmark layout scored better, replace `_fit` and `_direction` with `fit_landmark_basis` / `project_landmarks` from `scripts/measure_projection.py`, moving those functions into this module so nothing imports from `scripts/`.

```python
# server/projection.py
"""Turn a word and its score into a position on the board.

Radius comes from the score and is exact: it is the number Semantle
returned, so a point halfway to the centre really is 50%. Direction comes
from the word's meaning, via a projection basis fitted once at startup, so
a word always lands in the same direction and the board behaves like a map
rather than a re-shuffling cloud.

The basis is fitted from the vocabulary alone and never from the guesses,
so adding a guess never moves the points already on the board.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solver.vocabulary import Vocabulary

BOARD_RADIUS = 10.0
_FALLBACK_DIRECTION = np.array([0.0, 0.0, 1.0])


@dataclass(frozen=True)
class Position:
    x: float
    y: float
    z: float
    radius: float


class BoardProjection:
    def __init__(self, vocabulary: Vocabulary) -> None:
        self._mean = vocabulary.vectors.mean(axis=0)
        centred = vocabulary.vectors - self._mean
        _u, _s, vt = np.linalg.svd(centred, full_matrices=False)
        self._basis = vt[:3].T
        self._vocabulary = vocabulary

    def place(self, word: str, similarity: float) -> Position:
        index = self._vocabulary.word_to_index[word]
        return self.place_vector(self._vocabulary.vectors[index], similarity)

    def place_vector(self, vector: np.ndarray, similarity: float) -> Position:
        radius = BOARD_RADIUS * (1.0 - similarity / 100.0)
        direction = self._direction(vector)
        point = direction * radius
        return Position(
            x=float(point[0]), y=float(point[1]), z=float(point[2]), radius=float(radius)
        )

    def _direction(self, vector: np.ndarray) -> np.ndarray:
        projected = (vector - self._mean) @ self._basis
        length = np.linalg.norm(projected)
        if length == 0:
            return _FALLBACK_DIRECTION
        return projected / length
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_projection.py -v`
Expected: all PASS

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add server/__init__.py server/projection.py tests/test_projection.py
git commit -m "feat: deterministic board projection from score and meaning"
```

---

### Task 10: Dependencies and documentation

**Files:**
- Modify: `requirements.txt`, `README.md`
- Test: none

- [ ] **Step 1: Rewrite requirements.txt**

```
# Solver core
numpy>=2.3
requests>=2.34

# Terminal chart only
matplotlib>=3.11

# Tests
pytest>=8.4
```

- [ ] **Step 2: Update the README's setup and run sections**

Replace the "התקנה והרצה" section with:

```markdown
## התקנה והרצה

1. התקנת תלויות:
   pip install -r requirements.txt

2. הורדת מודל הוקטורים:
   curl -L -o data/wiki.he.vec \
     https://dl.fbaipublicfiles.com/fasttext/vectors-wiki/wiki.he.vec

3. בניית ארטיפקט אוצר המילים (פעם אחת):
   python -m scripts.build_vocab

4. הרצת הפותר:
   python run_cli.py

5. הרצת הבדיקות:
   python -m pytest
```

Replace the "מבנה הפרויקט" list with the package layout from this plan's File Structure table.

- [ ] **Step 3: Verify a clean run from the documented steps**

Run: `python -m pytest && python -m scripts.measure_projection`
Expected: tests PASS, measurement prints its comparison

- [ ] **Step 4: Commit**

```bash
git add requirements.txt README.md
git commit -m "docs: update setup for the new package layout"
```

---

## Self-Review

**Spec coverage.** Spec §3 structure → File Structure table plus Tasks 1-9. §4 geometry: radius mapping and determinism → Task 9; rings, zoom, labels, HUD, win state → deferred to the web plan by design. §5 event contract → Tasks 5-6. §6 projection measurement → Tasks 8-9. §7 the six confirmed fixes → bug 1, 2, 3 in Task 2; bug 4 in Task 6; bug 5 in Task 7; bug 6 in Task 4. §8 tests → Tasks 2, 3, 4, 6, 7, 9. §9 stages 1-3 → this plan; stages 4-5 → the follow-up web plan.

**Not covered here, by design:** `server/app.py`, `server/session.py`, and everything under `web/`. They are the follow-up plan, which consumes `SemantleEngine.run()` and `BoardProjection` unchanged.

**Type consistency.** `GuessResult(word, similarity, rank)` is produced in Task 4 and consumed in Task 6. `Vocabulary(words, vectors, word_to_index)` is produced in Task 3 and consumed in Tasks 6, 8, 9. `events.Guess` field names are identical in Tasks 5, 6 and 7. `BoardProjection.place` / `place_vector` / `Position` are used consistently in Task 9's tests and implementation.

**One deliberate behaviour change beyond the six fixes:** anchor probes now emit `Guess` events and increment `guess_number`, because they are real API calls that must appear on the board. `max_attempts` still bounds only the search phase, as before.
