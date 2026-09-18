import numpy as np
import pytest

from server.projection import BOARD_RADIUS, BoardProjection
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
    centre = projection.mean_vector
    first = projection.place_vector(centre, 50.0)
    second = projection.place_vector(centre, 50.0)
    length = np.linalg.norm([first.x, first.y, first.z])
    assert length == pytest.approx(first.radius, rel=1e-5)
    assert (first.x, first.y, first.z) == pytest.approx((second.x, second.y, second.z))


def test_an_unknown_word_is_rejected(vocabulary):
    with pytest.raises(KeyError):
        BoardProjection(vocabulary).place("מילהשאיננה", 50.0)


def test_a_stored_basis_is_used_instead_of_refitting(vocabulary, tmp_path):
    """SVD sign conventions are not stable across library versions, so a
    refit could mirror the board. The shipped basis settles it."""
    from server.projection import fit_basis, save_basis

    path = tmp_path / "projection.npz"
    mean, basis = fit_basis(vocabulary.vectors)
    save_basis(path, mean, -basis)  # deliberately flipped

    fitted = BoardProjection(vocabulary).place("כלב", 40.0)
    stored = BoardProjection(vocabulary, path).place("כלב", 40.0)
    assert stored.x == pytest.approx(-fitted.x)


def test_a_missing_basis_file_falls_back_to_fitting(vocabulary, tmp_path):
    projection = BoardProjection(vocabulary, tmp_path / "absent.npz")
    assert projection.place("כלב", 50.0).radius == pytest.approx(BOARD_RADIUS * 0.5)
