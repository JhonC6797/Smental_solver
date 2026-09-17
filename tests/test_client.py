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


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("semantle.client.time.sleep", lambda _seconds: None)


def _client(session):
    client = SemantleClient()
    client.session = session
    return client


def test_parses_similarity_and_rank():
    payload = [{"guess": "שלום", "similarity": 23.95, "distance": 847}]
    client = _client(FakeSession([FakeResponse(200, payload)]))
    assert client.get_similarity("שלום") == GuessResult("שלום", 23.95, 847)


def test_rank_is_none_when_outside_the_top_thousand():
    payload = [{"guess": "שלום", "similarity": 23.95, "distance": -1}]
    client = _client(FakeSession([FakeResponse(200, payload)]))
    assert client.get_similarity("שלום").rank is None


def test_the_secret_word_carries_the_highest_rank():
    """The answer itself is ranked 1000: a HIGHER rank means closer."""
    payload = [{"guess": "עץ", "similarity": 100.0, "distance": 1000}]
    client = _client(FakeSession([FakeResponse(200, payload)]))
    assert client.get_similarity("עץ").rank == 1000


def test_retries_once_after_a_rate_limit():
    payload = [{"guess": "אש", "similarity": 31.92, "distance": -1}]
    session = FakeSession([FakeResponse(429), FakeResponse(200, payload)])
    assert _client(session).get_similarity("אש").similarity == 31.92
    assert session.call_count == 2


def test_gives_up_after_the_retry_limit():
    """The original recursed without a bound and never returned."""
    session = FakeSession([FakeResponse(429)] * 10)
    assert _client(session).get_similarity("אש") is None
    assert session.call_count <= 4


def test_returns_none_on_an_empty_payload():
    client = _client(FakeSession([FakeResponse(200, [])]))
    assert client.get_similarity("אש") is None


def test_returns_none_when_the_request_raises():
    class ExplodingSession(FakeSession):
        def get(self, url, params=None, timeout=None):
            raise OSError("network down")

    assert _client(ExplodingSession([])).get_similarity("אש") is None
