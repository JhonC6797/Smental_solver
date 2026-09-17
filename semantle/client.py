"""HTTP client for the Semantle game API.

A successful response looks like:
    [{"guess": "שלום", "similarity": 23.95, "distance": -1,
      "egg": null, "solver_count": null, "guess_number": 0}]

`similarity` is a percentage on a 0-100 scale, and can be negative for a
word with no relation at all. Measured against the live API, ordinary
unrelated words land at 24-32 rather than 0.

`distance` is the guess's position in the answer's thousand nearest words,
or -1 when it is outside them. Higher means closer: the secret word itself
is ranked 1000. It is an exact closeness signal from the game's own model,
and it is recorded and displayed but deliberately not fed to the search.
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
