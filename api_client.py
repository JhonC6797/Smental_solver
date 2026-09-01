import time
import requests
from config import API_URL

class SemantleAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def get_similarity(self, word: str) -> float:
        params = {'word': word}
        time.sleep(0.35)
        
        try:
            response = self.session.get(API_URL, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    sim = data[0].get('similarity')
                    return float(sim) if sim is not None else None
            elif response.status_code == 429:
                print("[RATE LIMIT] Waiting 5 seconds...")
                time.sleep(5)
                return self.get_similarity(word)
            return None
        except Exception:
            return None