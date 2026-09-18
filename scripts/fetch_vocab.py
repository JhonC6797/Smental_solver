"""Download the prebuilt vocabulary artifact.

The solver needs 26MB of word vectors that are not kept in git: a binary
that size would sit in the repository's history forever, and every rebuild
of the vocabulary would add another copy. It is published as a GitHub
release asset instead and fetched at deploy time.

Run on a fresh machine, or as a deploy build step:
    python -m scripts.fetch_vocab

Point VOCAB_RELEASE_URL at a different release to use another build.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

from server.projection import BASIS_FILENAME
from solver import config

DEFAULT_RELEASE_URL = (
    "https://github.com/JhonC6797/Smental_solver/releases/download/vocab-v1"
)
FILES = (config.VECTORS_FILENAME, config.WORDS_FILENAME, BASIS_FILENAME)


def fetch(base_url: str, force: bool = False) -> None:
    config.VOCAB_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = config.VOCAB_DIR / name
        if target.exists() and not force:
            print(f"{name} is already here")
            continue
        url = f"{base_url.rstrip('/')}/{name}"
        print(f"Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, target)
        except urllib.error.HTTPError as error:
            target.unlink(missing_ok=True)
            raise SystemExit(
                f"Could not download {url} ({error.code}).\n"
                "Check that the release exists and has this file attached, "
                "or build the vocabulary locally with: python -m scripts.build_vocab"
            ) from error
        print(f"  saved to {target} ({target.stat().st_size // 1024} KB)")


def main() -> None:
    fetch(os.getenv("VOCAB_RELEASE_URL", DEFAULT_RELEASE_URL))
    print(f"\nVocabulary ready in {config.VOCAB_DIR}")


if __name__ == "__main__":
    main()
