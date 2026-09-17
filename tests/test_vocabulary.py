import numpy as np
import pytest

from solver.vocabulary import build_vocabulary, load_vocabulary


@pytest.fixture
def fake_vec_file(tmp_path):
    """A miniature .vec file in the real format: a header line of
    '<word count> <dimensions>', then one line per word."""
    path = tmp_path / "fake.vec"
    rows = [
        ("שלום", [3.0, 4.0, 0.0]),    # norm 5, kept
        (",", [1.0, 0.0, 0.0]),        # punctuation, dropped
        ("אש", [0.0, 2.0, 0.0]),       # two letters, kept
        ("rubbish", [1.0, 1.0, 1.0]),  # latin, dropped
        ("סוכר", [0.0, 0.0, 7.0]),     # kept
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
