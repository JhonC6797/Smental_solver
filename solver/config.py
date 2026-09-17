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
