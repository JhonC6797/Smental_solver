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
