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
