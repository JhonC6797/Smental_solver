import os

MODEL_PATH = "wiki.he.vec"
VOCAB_LIMIT = 80000
API_URL = "https://semantle.ishefi.com/api/distance"

INITIAL_ANCHORS = [
    "בית", "מלחמה", "ספר", "אוכל", "אדם", 
    "מחשב", "מדינה", "ארץ", "שמיים", "אש", 
    "ים", "שיר", "חוק", "נסיעה", "רופא"
]